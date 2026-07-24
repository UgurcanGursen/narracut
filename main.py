import sys
import os
import json

try:
    from v2.main import process_timeline, detect_timeline_format
    from v2.models import convert_v1_to_v2, TimelineV2, TimelineValidator
except ImportError as e:
    print("FATAL ERROR: Package 'v2' could not be imported.")
    print("Please run this script as: python -m v2.main timeline.json")
    print("Or ensure your current working directory is the project root.")
    print(f"Exception: {e}")
    sys.exit(1)

def run_validation(json_path: str):
    print(f"Validating {json_path}...")
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    format_type = detect_timeline_format(data)
    if format_type == "v1":
        timeline = convert_v1_to_v2(data)
    elif format_type == "v2_blocks_list":
        timeline = TimelineV2(blocks=data)
    else:
        timeline = TimelineV2(**data)
        
    validator = TimelineValidator()
    val_report = validator.validate(timeline)
    
    print("\n=== VALIDATION REPORT ===")
    for err in val_report["errors"]: print(f"  [ERROR] {err}")
    for wrn in val_report["warnings"]: print(f"  [WARN] {wrn}")
    
    if val_report["is_valid"]:
        print("\n[SUCCESS] Timeline is VALID!")
    else:
        print("\n[FAILED] Timeline is INVALID!")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--validate-only":
            target = sys.argv[2] if len(sys.argv) > 2 else "timeline.json"
            if os.path.exists(target):
                run_validation(target)
            else:
                print(f"File not found: {target}")
        else:
            process_timeline(sys.argv[1])
    else:
        if os.path.exists("timeline.json"):
            process_timeline("timeline.json")
        else:
            print("Please provide a timeline JSON file.")
            print("Usage: python main.py <timeline_json_path>")
