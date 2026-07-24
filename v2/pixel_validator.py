import os
import subprocess
import json
import numpy as np
import cv2

# Thresholds that can be moved to a config later
PIXEL_CONFIG = {
    "near_blank_luma_min": 230,
    "near_blank_luma_max": 255,  # allowing for near-white
    "near_blank_std_max": 15,
    "near_blank_edge_max": 10.0, # edge density threshold
    "near_identical_diff_max": 5.0, # frame difference threshold for "identical"
    
    # Validation gates
    "max_continuous_blank_s": 0.5,
    "max_total_blank_ratio": 0.01,
    "max_continuous_black_s": 0.5,
    "max_total_black_ratio": 0.01,
    "max_near_identical_ratio": 0.85,
    "max_longest_static_s": 5.5,
}

def _get_video_info(video_path: str):
    cmd = [
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height,avg_frame_rate,duration",
        "-of", "json", video_path
    ]
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.PIPE).decode('utf-8')
        info = json.loads(out)["streams"][0]
        w = int(info["width"])
        h = int(info["height"])
        fps_str = info["avg_frame_rate"].split('/')
        fps = float(fps_str[0]) / float(fps_str[1]) if len(fps_str) == 2 else float(info["avg_frame_rate"])
        duration = float(info["duration"])
        return w, h, fps, duration
    except Exception as e:
        print(f"Error getting video info: {e}")
        return None, None, None, None

def _extract_frames_ffmpeg(video_path: str, w: int, h: int, sample_fps: float = 5.0):
    """
    Extracts frames using FFmpeg to stdout and yields them as numpy arrays.
    """
    frame_size = w * h * 3
    cmd = [
        "ffmpeg", "-i", video_path,
        "-vf", f"fps={sample_fps}",
        "-f", "image2pipe",
        "-pix_fmt", "bgr24",
        "-vcodec", "rawvideo",
        "-"
    ]
    
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=10**8)
    
    while True:
        raw_frame = proc.stdout.read(frame_size)
        if len(raw_frame) != frame_size:
            break
        frame = np.frombuffer(raw_frame, dtype=np.uint8).reshape((h, w, 3))
        yield frame
        
    proc.stdout.close()
    proc.wait()

def compute_frame_metrics(frame: np.ndarray):
    """
    Computes mean luminance, std deviation, and edge density using OpenCV.
    """
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    mean_luma = np.mean(gray)
    std_dev = np.std(gray)
    
    # Edge density using Canny
    edges = cv2.Canny(gray, 50, 150)
    edge_density = np.mean(edges) / 255.0 * 100.0
    
    return gray, mean_luma, std_dev, edge_density

def compute_frame_difference(gray1: np.ndarray, gray2: np.ndarray):
    """
    Computes Mean Absolute Difference between two grayscale frames.
    """
    diff = cv2.absdiff(gray1, gray2)
    return np.mean(diff)

def analyze_video(video_path: str, sample_fps: float = 5.0) -> dict:
    import time
    start_t = time.time()
    
    w, h, fps, duration = _get_video_info(video_path)
    if w is None:
        return {"status": "error", "message": "Failed to read video with ffprobe"}
        
    frame_interval = 1.0 / sample_fps
    
    total_frames = 0
    blank_frames = 0
    black_frames = 0
    identical_frames = 0
    
    continuous_blank_intervals = 0
    continuous_static_intervals = 0
    
    current_blank_streak = 0
    max_blank_streak = 0
    
    current_black_streak = 0
    max_black_streak = 0
    
    current_static_streak = 0
    max_static_streak = 0
    
    prev_gray = None
    
    for frame in _extract_frames_ffmpeg(video_path, w, h, sample_fps):
        total_frames += 1
        gray, mean_luma, std_dev, edge_density = compute_frame_metrics(frame)
        
        # Check near-blank (white/gray placeholder)
        is_blank = (mean_luma > PIXEL_CONFIG["near_blank_luma_min"] and 
                    std_dev < PIXEL_CONFIG["near_blank_std_max"] and 
                    edge_density < PIXEL_CONFIG["near_blank_edge_max"])
        
        if is_blank:
            blank_frames += 1
            if current_blank_streak == 0:
                continuous_blank_intervals += 1
            current_blank_streak += 1
        else:
            if current_blank_streak > max_blank_streak:
                max_blank_streak = current_blank_streak
            current_blank_streak = 0
                    
        # Check pure black
        is_black = (mean_luma < 10.0 and std_dev < 5.0)

        if is_black:
            black_frames += 1
            current_black_streak += 1
        else:
            if current_black_streak > max_black_streak:
                max_black_streak = current_black_streak
            current_black_streak = 0
        
        # Check frame difference for static analysis
        is_identical = False
        if prev_gray is not None:
            diff = compute_frame_difference(prev_gray, gray)
            if diff < PIXEL_CONFIG["near_identical_diff_max"]:
                is_identical = True
                identical_frames += 1
                if current_static_streak == 0:
                    continuous_static_intervals += 1
                current_static_streak += 1
            else:
                if current_static_streak > max_static_streak:
                    max_static_streak = current_static_streak
                current_static_streak = 0
                
        prev_gray = gray

    if total_frames == 0:
        return {"status": "error", "message": "No frames extracted"}

    blank_ratio = blank_frames / total_frames
    identical_ratio = identical_frames / total_frames
    longest_blank_s = max_blank_streak * frame_interval
    longest_black_s = max_black_streak * frame_interval
    longest_static_s = max_static_streak * frame_interval

    status = "valid"
    reasons = []
    
    if longest_blank_s > PIXEL_CONFIG["max_continuous_blank_s"]:
        status = "invalid"
        reasons.append(f"Continuous blank frames exceeded limit: {longest_blank_s:.2f}s")
        
    if blank_ratio > PIXEL_CONFIG["max_total_blank_ratio"]:
        status = "invalid"
        reasons.append(f"Total near-blank ratio exceeded limit: {blank_ratio:.2%}")
        
    black_ratio = black_frames / total_frames if total_frames > 0 else 0
    if black_ratio > PIXEL_CONFIG["max_total_black_ratio"]:
        status = "invalid"
        reasons.append(f"Total black ratio exceeded limit: {black_ratio:.2%}")
        
    if longest_black_s > PIXEL_CONFIG["max_continuous_black_s"]:
        status = "invalid"
        reasons.append(f"Continuous black frames exceeded limit: {longest_black_s:.2f}s")
        
    if identical_ratio > PIXEL_CONFIG["max_near_identical_ratio"]:
        status = "invalid"
        reasons.append(f"Near-identical frame ratio exceeded limit: {identical_ratio:.2%}")
        
    if longest_static_s > PIXEL_CONFIG["max_longest_static_s"]:
        status = "invalid"
        reasons.append(f"Longest static interval exceeded limit: {longest_static_s:.2f}s")

    elapsed_seconds = time.time() - start_t
    
    return {
        "status": status,
        "analysis_backend": "opencv_ffmpeg_pipe",
        "sample_fps": sample_fps,
        "total_frames_sampled": total_frames,
        "near_black_ratio": round(black_frames / total_frames if total_frames else 0.0, 4),
        "near_blank_ratio": round(blank_ratio, 4),
        "near_identical_ratio": round(identical_ratio, 4),
        "longest_blank_s": round(longest_blank_s, 2),
        "longest_black_s": round(longest_black_s, 2),
        "longest_static_s": round(longest_static_s, 2),
        "continuous_blank_intervals": continuous_blank_intervals,
        "continuous_static_intervals": continuous_static_intervals,
        "elapsed_seconds": round(elapsed_seconds, 2),
        "thresholds": PIXEL_CONFIG,
        "reasons": reasons
    }
