import os
import sys
import uuid
import json
import subprocess
import shutil

FIXTURES_DIR = os.path.join("tests", "fixtures")
BASE_OUT = os.path.join("output", "closure_verification")

fixtures = [
    {
        "name": "ibm_v3_negative_coverage.json",
        "expected_acceptance": "failed",
        "expected_reason": "COVERAGE_INVALID"
    },
    {
        "name": "ibm_v3_negative_overlap.json",
        "expected_acceptance": "failed",
        "expected_reason": "OVERLAP_DETECTED"
    },
    {
        "name": "ibm_v3_negative_unresolved.json",
        "expected_acceptance": "failed",
        "expected_reason": "ASSET_UNRESOLVED"
    },
    {
        "name": "ibm_v3_negative_alignment.json",
        "expected_acceptance": "failed",
        "expected_reason": "ALIGNMENT_FAILED"
    },
    {
        "name": "ibm_v3_negative_consecutive_bridge.json",
        "expected_acceptance": "failed",
        "expected_reason": "CONSECUTIVE_BRIDGES"
    },
    {
        "name": "ibm_v3_negative_bridge_reuse.json",
        "expected_acceptance": "failed",
        "expected_reason": "BRIDGE_REUSED"
    },
    {
        "name": "ibm_v3_positive_acceptance.json",
        "expected_acceptance": "valid",
        "expected_reason": "NONE"
    }
]

def run_test(fixture, run_id):
    timeline = os.path.join(FIXTURES_DIR, fixture["name"])
    print(f"Running test for {fixture['name']}...")
    
    if os.path.exists("output/validation_report.json"):
        os.remove("output/validation_report.json")
        
    cmd = [
        sys.executable, "-m", "v2.main",
        timeline,
        "--render-mode", "production"
    ]
    
    proc = subprocess.run(cmd, capture_output=True, text=True)
    
    val_path = "output/validation_report.json"
    if not os.path.exists(val_path):
        print(f"  [ERROR] {val_path} not found.")
        print(proc.stderr)
        return False
        
    with open(val_path, "r", encoding="utf-8") as f:
        val = json.load(f)
        
    acc_status = val.get("acceptance_status")
    print(f"  acceptance_status: {acc_status}")
    
    success = True
    if acc_status != fixture["expected_acceptance"]:
        print(f"  [ERROR] Expected {fixture['expected_acceptance']}, got {acc_status}")
        success = False
        
    dest = os.path.join(BASE_OUT, run_id, fixture["name"].replace(".json", ""))
    os.makedirs(dest, exist_ok=True)
    
    for f in os.listdir("output"):
        if f.endswith(".json") or f.endswith(".mp4"):
            shutil.copy2(os.path.join("output", f), dest)
            
    return success

def main():
    run_id = f"closure_run_{uuid.uuid4().hex[:6]}"
    os.makedirs(os.path.join(BASE_OUT, run_id), exist_ok=True)
    print(f"Starting Verification Run: {run_id}")
    
    all_passed = True
    for fix in fixtures:
        if not run_test(fix, run_id):
            all_passed = False
            
    print("\n--------------------------")
    if all_passed:
        print("ALL TESTS PASSED SUCCESSFULLY.")
    else:
        print("SOME TESTS FAILED.")
        
if __name__ == "__main__":
    main()