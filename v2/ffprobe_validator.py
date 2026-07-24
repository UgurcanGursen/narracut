import os
import json
import subprocess
import shutil

def validate_and_move_if_corrupt(file_path: str, expected_duration: float = None, corrupt_dir: str = None) -> dict:
    res = validate_video_file(file_path, expected_duration)
    if not res["valid"] and corrupt_dir and os.path.exists(file_path):
        try:
            base = os.path.basename(file_path)
            dest = os.path.join(corrupt_dir, base)
            shutil.move(file_path, dest)
            res["moved_to_corrupt"] = True
        except Exception:
            try:
                os.remove(file_path)
            except:
                pass
    return res

def validate_video_file(file_path: str, expected_duration: float = None) -> dict:
    """
    Validates a video file using ffprobe.
    Returns: {"valid": bool, "reason": str}
    """
    if not os.path.exists(file_path):
        return {"valid": False, "reason": "file_not_found"}
        
    size = os.path.getsize(file_path)
    if size < 10240: # 10 KB
        return {"valid": False, "reason": f"file_too_small_{size}B"}
        
    cmd = [
        "ffprobe", 
        "-v", "error", 
        "-select_streams", "v:0", 
        "-show_entries", "format=duration:stream=width,height,codec_name", 
        "-of", "json", 
        file_path
    ]
    
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
        if res.returncode != 0:
            return {"valid": False, "reason": "ffprobe_error"}
            
        data = json.loads(res.stdout.decode("utf-8"))
        
        streams = data.get("streams", [])
        if not streams:
            return {"valid": False, "reason": "no_video_stream"}
            
        stream = streams[0]
        w = stream.get("width", 0)
        h = stream.get("height", 0)
        
        if w <= 0 or h <= 0:
            return {"valid": False, "reason": "invalid_resolution"}
            
        # Duration check
        fmt = data.get("format", {})
        duration_str = fmt.get("duration")
        if not duration_str:
            return {"valid": False, "reason": "no_duration"}
            
        actual_duration = float(duration_str)
        
        if actual_duration <= 0:
            return {"valid": False, "reason": "zero_duration"}
            
        if expected_duration is not None and expected_duration > 0:
            min_dur = expected_duration - 0.3
            max_dur = expected_duration + 0.75
            
            if not (min_dur <= actual_duration <= max_dur):
                return {"valid": False, "reason": f"duration_mismatch_expected_{expected_duration}_got_{actual_duration}"}
                
        return {"valid": True, "reason": "ok"}
        
    except subprocess.TimeoutExpired:
        return {"valid": False, "reason": "ffprobe_timeout"}
    except Exception as e:
        return {"valid": False, "reason": f"exception_{str(e)}"}
