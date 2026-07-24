import os
import glob
import random
import requests
import hashlib

from .cache_manager import CACHE_BASE
from .config import YOUTUBE_DEFAULT_MAX_HEIGHT, YOUTUBE_ZOOMED_MAX_HEIGHT, PEXELS_API_KEY
from .youtube_state_machine import YouTubeDownloadStateMachine
from .asset_approval import compute_file_fingerprint

_URL_COUNTS = {}

def init_grouping(timeline_blocks: list):
    global _URL_COUNTS
    _URL_COUNTS.clear()
    for block in timeline_blocks:
        for vis in block.visuals:
            if vis.type == "youtube" and vis.url:
                _URL_COUNTS[vis.url] = _URL_COUNTS.get(vis.url, 0) + 1

def _safe_video_id(url: str) -> str:
    return hashlib.md5(url.encode("utf-8")).hexdigest()[:12]

def _simplify_query(query: str) -> str:
    if not query: return ""
    words = query.split()
    if len(words) <= 3:
        return query
    # take first, middle, last
    return " ".join([words[0], words[len(words)//2], words[-1]])

def fetch_pexels_video(
    query: str, 
    fallback_queries: list = None, 
    allow_generic: bool = True, 
    expected_duration: float = 0.0,
    visual_purpose: str = "",
    required_content: list = None,
    forbidden_content: list = None,
    previously_used_urls: set = None
) -> dict:
    if not previously_used_urls:
        previously_used_urls = set()
        
    if not PEXELS_API_KEY:
        local_stock = os.path.join("assets", "videos")
        if os.path.isdir(local_stock):
            files = sorted(glob.glob(os.path.join(local_stock, "*.mp4")))
            if files:
                path = files[0]
                return {"path": path, "url": f"local:{os.path.basename(path)}", "title": os.path.basename(path), "provider": "local", "review_required": True}
        return None
        
    headers = {"Authorization": PEXELS_API_KEY}
    
    queries_to_try = [query]
    if fallback_queries:
        queries_to_try.extend(fallback_queries)
    queries_to_try.append(_simplify_query(query))
    if allow_generic:
        queries_to_try.append("abstract technology data center")
    
    from .config import STOCK_SEMANTIC_MIN_SCORE
    min_score_points = STOCK_SEMANTIC_MIN_SCORE * 100
    
    for q in queries_to_try:
        if not q: continue
        identifier = f"pexels_{hashlib.md5(q.encode('utf-8')).hexdigest()}"
        out_path = os.path.join(CACHE_BASE, f"{identifier}.mp4")
        if os.path.exists(out_path):
            return {"path": out_path, "url": f"pexels:{identifier}", "title": q, "provider": "pexels", "review_required": False}
            
        url = f"https://api.pexels.com/videos/search?query={q}&per_page=15&orientation=landscape"
        try:
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code == 200:
                data = res.json()
                videos = data.get("videos", [])
                if videos:
                    def score_video(v):
                        score = 0.0
                        width = v.get("width", 0)
                        height = v.get("height", 0)
                        dur = v.get("duration", 0)
                        v_url = v.get("url", "")
                        
                        v_text = v_url.lower().replace("-", " ")
                        
                        semantic_score = 0.0
                        query_words = q.lower().split()
                        matched_q = sum(1 for qw in query_words if qw in v_text)
                        if query_words:
                            semantic_score = (matched_q / len(query_words))
                        score += semantic_score * 45
                        
                        req_score = 0.0
                        if required_content:
                            matched_r = sum(1 for req in required_content if req.lower() in v_text)
                            req_score = (matched_r / len(required_content))
                        else:
                            req_score = 1.0
                        score += req_score * 20
                        
                        if forbidden_content:
                            for f in forbidden_content:
                                if f.lower() in v_text:
                                    return (-1000, v.get("id", 0))
                        score += 15
                        
                        if width > height: score += 8
                        if width >= 1920: score += 5
                        elif width >= 1280: score += 2.5
                        
                        if dur >= expected_duration: score += 4
                        if v_url not in previously_used_urls: score += 3
                            
                        return (score, v.get("id", 0))
                        
                    videos.sort(key=score_video, reverse=True)
                    best_video = videos[0]
                    best_score = score_video(best_video)[0]
                    
                    # If highest score is still negative, then forbidden content was hit on all or something is wrong
                    if best_score < 0:
                        print(f"  [STOCK WARNING] All candidates rejected due to semantic/forbidden criteria for '{q}'")
                        continue
                        
                    # Semantic stats for manifest
                    v_url = best_video.get("url", "")
                    v_text = v_url.lower().replace("-", " ")
                    req_met = False
                    if required_content:
                        req_met = sum(1 for req in required_content if req.lower() in v_text) > 0
                    else:
                        req_met = True
                    forb_met = False
                    if forbidden_content:
                        forb_met = any(f.lower() in v_text for f in forbidden_content)
                        
                    thumbnail_url = best_video.get("image", "")
                    
                    video_files = best_video.get("video_files", [])
                    hd_files = [f for f in video_files if f.get("quality") == "hd" and f.get("width", 0) >= 1280]
                    if not hd_files and video_files:
                        hd_files = video_files
                    if hd_files:
                        target_url = hd_files[0]["link"]
                        v_res = requests.get(target_url, stream=True, timeout=15)
                        if v_res.status_code == 200:
                            with open(out_path, "wb") as f:
                                for chunk in v_res.iter_content(chunk_size=1024*1024):
                                    f.write(chunk)
                            return {
                                "path": out_path, 
                                "url": best_video.get("url", target_url), 
                                "title": best_video.get("url", q).split('/')[-2] if "url" in best_video else q, 
                                "provider": "pexels",
                                "review_required": True,
                                "semantic_score": round(best_score, 1),
                                "thumbnail": thumbnail_url,
                                "query": q,
                                "visual_purpose": visual_purpose,
                                "required_content_met": req_met,
                                "forbidden_content_met": forb_met
                            }
            elif res.status_code == 429:
                print(f"  [PEXELS WARNING] Rate limit exceeded on query '{q}'.")
            else:
                print(f"  [PEXELS WARNING] Status {res.status_code} for query '{q}'.")
        except Exception as e:
            print(f"  [PEXELS WARNING] Request failed for query '{q}' ({type(e).__name__}).")
            
    return None

def resolve_visual_asset(
    visual_type: str, url: str = None, query: str = None, 
    clip_start: float = 0, clip_end: float = 0,
    max_height: int = None, crop_mode: str = "none", scene_id: str = "youtube_scene",
    fallback_queries: list = None, allow_generic: bool = True,
    visual_purpose: str = "", required_content: list = None, forbidden_content: list = None,
    previously_used_urls: set = None
) -> dict:
    fallback_used = False
    duration = clip_end - clip_start
    yt_log = None
    asset_meta = {}
    
    if forbidden_content is None:
        forbidden_content = []
    
    default_forbidden = ["external hard drive", "portable drive", "consumer storage", "desktop accessory"]
    for f in default_forbidden:
        if f not in forbidden_content:
            forbidden_content.append(f)
    
    if visual_type == "youtube" and url:
        mh = max_height
        if mh is None:
            if crop_mode != "none":
                mh = YOUTUBE_ZOOMED_MAX_HEIGHT
            else:
                mh = YOUTUBE_DEFAULT_MAX_HEIGHT
                
        req_count = _URL_COUNTS.get(url, 1)
        video_id = _safe_video_id(url)
        
        machine = YouTubeDownloadStateMachine(
            video_id=video_id, url=url, clip_start=clip_start, 
            duration=duration, max_height=mh, crop_mode=crop_mode, 
            request_count=req_count
        )
        
        yt_res = machine.run()
        yt_log = yt_res
        
        if yt_res["result"] == "success":
            fingerprint = compute_file_fingerprint(yt_res["path"])
            return {"path": yt_res["path"], "fallback_used": False, "type_used": "youtube", "log": yt_log, 
                    "asset_url": url, "asset_title": f"YouTube:{video_id}", "asset_provider": "youtube",
                    "content_fingerprint": fingerprint}
            
        print(f"  [FALLBACK] YouTube failed for {url}. Falling back to stock.")
        from .config import ENABLE_AUTOMATIC_STOCK_FALLBACK
        if not ENABLE_AUTOMATIC_STOCK_FALLBACK:
            return {"path": None, "fallback_used": True, "type_used": "none", "log": yt_log,
                    "asset_url": None, "asset_title": None, "asset_provider": None, "review_required": False}
        fallback_used = True
        visual_type = "stock"
        query = query if query else "abstract background"
        
    if visual_type == "stock":
        res_dict = fetch_pexels_video(query, fallback_queries, allow_generic, duration, visual_purpose, required_content, forbidden_content, previously_used_urls)
        if res_dict:
            fingerprint = compute_file_fingerprint(res_dict["path"])
            return {"path": res_dict["path"], "fallback_used": fallback_used, "type_used": "stock", "log": yt_log,
                    "asset_url": res_dict.get("url"), "asset_title": res_dict.get("title"), "asset_provider": res_dict.get("provider"),
                    "review_required": res_dict.get("review_required", False), "semantic_score": res_dict.get("semantic_score", 0.0),
                    "content_fingerprint": fingerprint}
            
        import os
        import subprocess
        fallback_dir = os.path.join("cache", "generated_fallbacks", "v1", str(scene_id or "default"))
        os.makedirs(fallback_dir, exist_ok=True)
        import hashlib
        safe_id = "".join(c if c.isalnum() else "_" for c in str(scene_id or "default"))
        h = int(hashlib.md5(safe_id.encode()).hexdigest(), 16)
        hue_offset = (h % 100) / 100.0 * 2 * 3.14159
        
        path = os.path.join(fallback_dir, f"fallback_{safe_id}.mp4")
        if not os.path.exists(path):
            cmd = [
                'ffmpeg', '-y', '-f', 'lavfi', 
                '-i', f'testsrc=duration={duration if duration > 0 else 5.0}:size=1920x1080:rate=30',
                '-vf', f"drawtext=text='{safe_id}':x=w-t*200:y=h/2:fontsize=100:fontcolor=white, hue=H={hue_offset}+2*PI*t/10",
                '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '20', path
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
        fingerprint = compute_file_fingerprint(path)
        return {"path": path, "fallback_used": True, "type_used": "local_fallback", "log": yt_log,
                "asset_url": f"local:{os.path.basename(path)}", "asset_title": safe_id, "asset_provider": "local",
                "content_fingerprint": fingerprint}
                
    return {"path": None, "fallback_used": True, "type_used": "none", "log": yt_log,
            "asset_url": None, "asset_title": None, "asset_provider": None, "content_fingerprint": "none"}
