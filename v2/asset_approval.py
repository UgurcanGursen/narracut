import os
import json
import hashlib
from datetime import datetime

APPROVAL_DB_PATH = os.path.join(os.getcwd(), "assets", "approval_db.json")

def _load_db():
    if os.path.exists(APPROVAL_DB_PATH):
        with open(APPROVAL_DB_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def _save_db(db):
    os.makedirs(os.path.dirname(APPROVAL_DB_PATH), exist_ok=True)
    with open(APPROVAL_DB_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2)

def generate_approval_fingerprint(visual_type: str, visual_purpose: str, crop_mode: str, source_range: str = "") -> str:
    # Deprecated/Fallback for pre-resolution approval.
    payload = f"{visual_type}|{visual_purpose}|{crop_mode}|{source_range}".encode("utf-8")
    return hashlib.md5(payload).hexdigest()

def compute_file_fingerprint(file_path: str) -> str:
    if not os.path.exists(file_path):
        return None
        
    sidecar_path = f"{file_path}.fingerprint.json"
    stat = os.stat(file_path)
    file_size = stat.st_size
    mtime_ns = stat.st_mtime_ns
    
    if os.path.exists(sidecar_path):
        try:
            with open(sidecar_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if data.get("file_size") == file_size and data.get("mtime_ns") == mtime_ns:
                    return data.get("content_fingerprint")
        except:
            pass
            
    # Compute SHA-256
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
            
    fp = hasher.hexdigest()
    
    # Save sidecar
    with open(sidecar_path, "w", encoding="utf-8") as f:
        json.dump({
            "content_fingerprint": fp,
            "file_size": file_size,
            "mtime_ns": mtime_ns,
            "hash_algorithm": "sha256"
        }, f, indent=2)
        
    return fp

def get_canonical_usage_key(content_fingerprint: str, selected_range: str, crop_mode: str, fit_mode: str) -> str:
    payload = {
        "content_fingerprint": content_fingerprint,
        "selected_range": selected_range or "full",
        "crop_mode": crop_mode or "none",
        "fit_mode": fit_mode or "cover"
    }
    # JSON serialized payload with sorted keys and defined precision, hashed via SHA-256
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    
def get_generated_asset_usage_key(payload_hash: str, template_version: str = "v1", renderer_version: str = "v3.1") -> str:
    return f"generated|{payload_hash}|{template_version}|{renderer_version}"

def get_asset_status(asset_id: str, fingerprint: str) -> str:
    db = _load_db()
    entry = db.get(asset_id)
    if not entry:
        return None
    if entry.get("approved_fingerprint") == fingerprint:
        return entry.get("status")
    return None

def set_asset_status(asset_id: str, fingerprint: str, status: str):
    db = _load_db()
    db[asset_id] = {
        "status": status,
        "approved_fingerprint": fingerprint,
        "approved_at": datetime.now().isoformat()
    }
    _save_db(db)

def _find_shot(timeline_path: str, shot_id: str):
    with open(timeline_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    for b in data.get("beats", []):
        for s in b.get("shots", []):
            if s.get("shot_id") == shot_id:
                return s
    return None

def cli_approve_asset(timeline_path: str, shot_id: str):
    shot = _find_shot(timeline_path, shot_id)
    if not shot:
        print(f"Shot '{shot_id}' not found.")
        return
        
    fp = generate_approval_fingerprint(shot.get("visual_type",""), shot.get("visual_purpose",""), shot.get("crop_mode",""))
    set_asset_status(shot_id, fp, "approved")
    print(f"[SUCCESS] Approved asset for {shot_id}")

def cli_reject_asset(timeline_path: str, shot_id: str):
    shot = _find_shot(timeline_path, shot_id)
    if not shot:
        print(f"Shot '{shot_id}' not found.")
        return
        
    fp = generate_approval_fingerprint(shot.get("visual_type",""), shot.get("visual_purpose",""), shot.get("crop_mode",""))
    set_asset_status(shot_id, fp, "rejected")
    print(f"[SUCCESS] Rejected asset for {shot_id}")

def cli_lock_asset(timeline_path: str, shot_id: str, url: str):
    shot = _find_shot(timeline_path, shot_id)
    if not shot:
        print(f"Shot '{shot_id}' not found.")
        return
    
    fp = generate_approval_fingerprint(shot.get("visual_type",""), shot.get("visual_purpose",""), shot.get("crop_mode",""))
    db = _load_db()
    db[shot_id] = {
        "status": "locked",
        "approved_fingerprint": fp,
        "locked_url": url,
        "approved_at": datetime.now().isoformat()
    }
    _save_db(db)
    print(f"[SUCCESS] Locked asset for {shot_id} to URL: {url}")

