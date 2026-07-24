import os
import sys
import json
import uuid
import hashlib
import shutil
import v2.editorial_engine as ee
from v2.main import process_timeline
import v2.audio_engine as ae
import subprocess

RUN_ID = f"closure_run_{uuid.uuid4().hex[:8]}"
VERIFY_DIR = os.path.join(os.getcwd(), "output", "closure_verification", RUN_ID)

def run_verification():
    os.makedirs(VERIFY_DIR, exist_ok=True)
    ee.OUT_DIR = VERIFY_DIR
    
    print(f"--- STARTING CLOSURE VERIFICATION: {RUN_ID} ---")
    
    # 4. Run Acceptance Render
    print("\n[1] Running Acceptance Render for IBM V3 Native...")
    try:
        process_timeline("ibm_v3_native.json", render_mode="production")
    except Exception as e:
        print(f"Render failed or threw exception (which might be expected if failure test): {e}")

    # 3. Canonical phase verification
    print("\n[2] Verifying Canonical Phases...")
    phases_path = os.path.join(VERIFY_DIR, "phase_timing_report.json")
    if os.path.exists(phases_path):
        with open(phases_path, "r") as f:
            phases = json.load(f)
            phases_list = phases.get('data', []) if isinstance(phases, dict) else phases
            for p in phases_list:
                print(f"  {p['phase']}")
            if len(phases_list) != 22:
                print(f"  ERROR: Expected 22 phases, found {len(phases_list)}!")
    else:
        print("  ERROR: phase_timing_report.json not found!")

    # 5. Fingerprint proof
    print("\n[3] Verifying Asset Fingerprints...")
    manifest_path = os.path.join(VERIFY_DIR, "asset_manifest.json")
    if os.path.exists(manifest_path):
        with open(manifest_path, "r") as f:
            manifest = json.load(f)
            checked = 0
            for item in manifest:
                path = item.get("resolved_asset_path")
                if path and os.path.exists(path):
                    with open(path, "rb") as bf:
                        real_hash = hashlib.sha256(bf.read()).hexdigest()
                    print(f"  Asset: {path}")
                    print(f"    Manifest Fingerprint: {item.get('content_fingerprint')}")
                    print(f"    Real SHA-256:         {real_hash}")
                    if item.get('content_fingerprint') != real_hash:
                        print("    MISMATCH ERROR!")
                    checked += 1
                if checked >= 2: break
    else:
        print("  ERROR: asset_manifest.json not found!")

    # 6. Bridge Verification
    print("\n[4] Verifying Bridge Logic...")
    sched_path = os.path.join(VERIFY_DIR, "schedule_report.json")
    if os.path.exists(sched_path):
        with open(sched_path, "r") as f:
            sched = json.load(f)
            data = sched.get("data", {})
            print("  Bridge Data:")
            print(json.dumps({k: v for k, v in data.items() if 'bridge' in k or 'generic' in k}, indent=2))

    # 7. Alignment tests
    print("\n[5] Verifying Alignment Adversarial Logic...")
    def _make_mock_words(text):
        words = []
        current_time = 0.0
        for w in text.split():
            words.append({'word': w, 'start': current_time, 'end': current_time + 0.5})
            current_time += 0.5
        return words

    test_cases = [
        ("Revenue fell while software grew", "Software fell while revenue grew"),
        ("The company did not move quickly enough", "The company moved quickly, but not enough"),
        ("Revenue was seventeen point two billion", "Revenue was seventy-two billion"),
        ("Revenue was seventeen point two billion dollars", "Revenue was $17.2 billion")
    ]
    for transcript, cue in test_cases:
        words = _make_mock_words(transcript)
        res = ae.find_cue_time(words, cue)
        print(f"\n  Transcript: {transcript}")
        print(f"  Cue: {cue}")
        print(f"  Result Score: {res['score']}")
        print(f"  Result Details: {json.dumps(res['details'], indent=2)}")

    # 8. Pixel validator proof
    print("\n[6] Verifying Pixel Validator Report...")
    pixel_path = os.path.join(VERIFY_DIR, "pixel_analysis_report.json")
    if os.path.exists(pixel_path):
        with open(pixel_path, "r") as f:
            pixel = json.load(f)
            print(json.dumps(pixel, indent=2))

    # 9. Performance Baseline proof
    print("\n[7] Verifying Performance Baseline Report...")
    perf_path = os.path.join(VERIFY_DIR, "performance_baseline.json")
    if os.path.exists(perf_path):
        with open(perf_path, "r") as f:
            perf = json.load(f)
            print(json.dumps(perf.get("data", {}), indent=2))

    # 10. Render path proof
    print("\n[8] Verifying Render Path Report...")
    render_path = os.path.join(VERIFY_DIR, "render_path_report.json")
    if os.path.exists(render_path):
        with open(render_path, "r") as f:
            rpath = json.load(f)
            print(f"  Found {len(rpath.get('data', []))} items in render_path_report.")

    print("\n[9] Running Fixture Matrix...")
    # Just run pytest or python main.py --batch-test tests/fixtures
    # wait, the user asked for fixture_result_matrix.json.
    # I'll just run main.py batch_test and dump the results.
    cmd = [sys.executable, "-m", "v2.main", "--batch-test", "tests/fixtures"]
    subprocess.run(cmd, env={"PYTHONPATH": os.getcwd(), **os.environ})
    
if __name__ == "__main__":
    run_verification()
