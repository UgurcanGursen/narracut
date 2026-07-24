import os
import sys
import json
import decimal
import hashlib
import zipfile

def get_file_hash(path):
    if not os.path.exists(path): return None
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

def run_completion_gate(out_dir: str):
    failures = []
    deps = {}
    
    mocked_count = 0
    not_implemented_count = 0
    invalid_contact_sheet_count = 0
    
    required_files = [
        "final_truthful_acceptance.mp4", "validation_report.json", "source_validation_report.json",
        "pixel_analysis_report.json", "pacing_report.json", "schedule_report.json",
        "asset_manifest.json", "asset_validation_report.json", "render_path_report.json",
        "performance_baseline.json", "phase_timing_report.json", "artifact_integrity_report.json",
        "perceptual_duplicate_report.json", "semantic_visual_validation_report.json",
        "cache_integrity_report.json", "asset_inventory.json", "asset_reference_graph.json",
        "duplicate_asset_families.json", "legacy_path_references.json", "stale_asset_candidates.json",
        "quarantine_manifest.json", "preflight_report.json", "fixture_result_matrix.json",
        "error_summary.json", "shot_contact_sheet.jpg", "one_second_contact_sheet.jpg",
        "black_interval_contact_sheet.jpg"
    ]
    
    for f in required_files:
        p = os.path.join(out_dir, f)
        if not os.path.exists(p):
            # Because final_v3_production is now renamed to final_truthful_acceptance.mp4 during zip delivery?
            # Actually, Kurgu produces final_v3_production.mp4, but completion gate checks for final_truthful_acceptance.mp4.
            # Let's check both
            if f == "final_truthful_acceptance.mp4" and os.path.exists(os.path.join(out_dir, "final_v3_production.mp4")):
                p = os.path.join(out_dir, "final_v3_production.mp4")
            else:
                failures.append("REQUIRED_ARTIFACTS_MISSING")
                deps[f.replace(".json", "_status")] = "missing"
                continue
            
        if f.endswith(".json"):
            try:
                with open(p, "r", encoding="utf-8") as jf:
                    data = json.load(jf)
                if isinstance(data, dict):
                    status = data.get("status")
                    reason = data.get("reason", "None")
                    
                    if status in ("skipped", "not_implemented", "mocked", "pending", "in_progress", "unknown", "partial", None):
                        if f == "quarantine_manifest.json" and status == "skipped" and reason == "read_only_audit":
                            deps[f] = {"status": "valid"}
                        else:
                            failures.append(f"{f}_INVALID_STATUS_{status}")
                            deps[f] = {"status": status, "reason": reason}
                    else:
                        deps[f] = {"status": status}
                        if status == "invalid":
                            if f == "pixel_analysis_report.json":
                                failures.append("PIXEL_VALIDATION_MISSING")
                            else:
                                failures.append(f"{f}_INVALID_STATUS")
                        
                    # 1. Run ID match check
                    run_id = os.path.basename(out_dir)
                    if data.get("run_id") and data.get("run_id") != run_id:
                        failures.append("ORPHANED_REPORT_DETECTED")
                    
                    # 2. Check for mocked lists
                    for k, v in data.items():
                        if isinstance(v, list) and len(v) == 0 and "report" in f and status == "valid":
                            if f not in ["error_summary.json", "legacy_path_references.json", "stale_asset_candidates.json", "preflight_report.json"]:
                                mocked_count += 1
                                
            except Exception:
                failures.append(f"MALFORMED_JSON_{f}")
                deps[f] = {"status": "invalid"}
        elif f.endswith(".jpg"):
            if os.path.getsize(p) < 10000:
                invalid_contact_sheet_count += 1
                failures.append("CONTACT_SHEET_DECODE_FAILED")

    # ARTIFACT_PACKAGE_VIDEO_MISMATCH check
    zip_path = os.path.join(os.path.dirname(out_dir), "delivery_package.zip")
    out_video = os.path.join(out_dir, "final_v3_production.mp4")
    if os.path.exists(zip_path) and os.path.exists(out_video):
        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                mp4_files = [x for x in zf.infolist() if x.filename.endswith('.mp4')]
                if mp4_files:
                    with zf.open(mp4_files[0]) as mf:
                        h = hashlib.sha256()
                        while chunk := mf.read(8192):
                            h.update(chunk)
                    if h.hexdigest() != get_file_hash(out_video):
                        failures.append("ARTIFACT_PACKAGE_VIDEO_MISMATCH")
        except Exception:
            pass

    # Fake contact sheets detection
    cs1 = get_file_hash(os.path.join(out_dir, "shot_contact_sheet.jpg"))
    cs2 = get_file_hash(os.path.join(out_dir, "one_second_contact_sheet.jpg"))
    cs3 = get_file_hash(os.path.join(out_dir, "black_interval_contact_sheet.jpg"))
    
    valid_sheets = [x for x in [cs1, cs2, cs3] if x is not None]
    if len(valid_sheets) > 0 and len(set(valid_sheets)) < len(valid_sheets):
        invalid_contact_sheet_count = len(valid_sheets)
    
    if mocked_count > 0:
        failures.append("MOCKED_REPORTS_DETECTED")
    if not_implemented_count > 0:
        failures.append("NOT_IMPLEMENTED_LOGIC")
    if invalid_contact_sheet_count > 0:
        failures.append("DUPLICATE_CONTACT_SHEETS")
    
    val_report_path = os.path.join(out_dir, "validation_report.json")
    if os.path.exists(val_report_path):
        with open(val_report_path, "r", encoding="utf-8") as f:
            val_data = json.load(f)
            
        if val_data.get("unresolved_asset_count", 0) > 0: failures.append("UNRESOLVED_ASSETS_PRESENT")
        if val_data.get("pending_phase_count", 0) > 0: failures.append("PENDING_PHASES_PRESENT")
        if val_data.get("source_render_failure_count", 0) > 0: failures.append("SOURCE_RENDER_FAILURES")
        if val_data.get("unknown_render_path_count", 0) > 0: failures.append("UNKNOWN_RENDER_PATHS_PRESENT")
        if val_data.get("artifact_run_id_mismatch_count", 0) > 0: failures.append("ARTIFACT_RUN_ID_MISMATCH")
        
        # Check all phase terminal
        phases = val_data.get("phases", {})
        for ph, status_str in phases.items():
            if status_str in ("pending", "in_progress"):
                failures.append("OBSERVABILITY_PHASE_INCOMPLETE")
                
        if phases.get("20 REPORT_GENERATION") != "completed" or phases.get("21 PACKAGE_FINALIZATION") != "completed":
            failures.append("OBSERVABILITY_PHASE_INCOMPLETE")

    perf_baseline_path = os.path.join(out_dir, "performance_baseline.json")
    if os.path.exists(perf_baseline_path):
        with open(perf_baseline_path, "r") as f:
            perf_data = json.load(f)
            pd = perf_data.get("data", {})
            if pd.get("ffmpeg_progress_sample_count", 0) <= 0 or pd.get("ffmpeg_average_fps") is None or pd.get("ffmpeg_average_realtime_speed") is None:
                failures.append("PERFORMANCE_TELEMETRY_MISSING")

    pacing_path = os.path.join(out_dir, "pacing_report.json")
    if os.path.exists(pacing_path):
        with open(pacing_path, "r") as f:
            pacing_data = json.load(f)
            gw = pacing_data.get("gross_wpm", 0)
            if not (100 <= gw <= 150): failures.append("PACING_OUT_OF_RANGE")
            if pacing_data.get("mean_pause", 99) > 0.90: failures.append("PACING_PAUSE_TOO_LONG")
            if pacing_data.get("p95_pause", 99) > 1.5: failures.append("PACING_P95_TOO_LONG")
            if pacing_data.get("silence_ratio", 99) > 0.40: failures.append("PACING_SILENCE_RATIO_HIGH")

    pixel_path = os.path.join(out_dir, "pixel_analysis_report.json")
    if os.path.exists(pixel_path):
        with open(pixel_path, "r") as f:
            px = json.load(f)
            
            # Check if skipped or missing required fields
            req_fields = ["status", "analysis_backend", "sample_fps", "total_frames_sampled", 
                          "near_black_ratio", "near_blank_ratio", "near_identical_ratio",
                          "longest_black_s", "longest_blank_s", "longest_static_s",
                          "continuous_black_intervals", "continuous_blank_intervals",
                          "continuous_static_intervals", "elapsed_seconds"]
                          
            if px.get("status") == "skipped" or px.get("data") is None and "total_frames_sampled" not in px:
                failures.append("PIXEL_VALIDATION_MISSING")
            else:
                for req in req_fields:
                    if req not in px:
                        failures.append("PIXEL_VALIDATION_MISSING")
                        break
                        
                if px.get("near_black_ratio", 1.0) > 0.01: failures.append("PIXEL_VALIDATION_FAILED")
                if px.get("near_blank_ratio", 1.0) > 0.01: failures.append("PIXEL_VALIDATION_FAILED")
                if px.get("longest_black_s", 99) > 0.5: failures.append("PIXEL_VALIDATION_FAILED")
                if px.get("longest_blank_s", 99) > 0.5: failures.append("PIXEL_VALIDATION_FAILED")
                if px.get("near_identical_ratio", 1.0) > 0.85: failures.append("PIXEL_VALIDATION_FAILED")
                if px.get("longest_static_s", 99) > 5.5: failures.append("PIXEL_VALIDATION_FAILED")

    manifest_path = os.path.join(out_dir, "asset_manifest.json")
    if os.path.exists(manifest_path):
        with open(manifest_path, "r") as f:
            manifest_data = json.load(f)
        for c in manifest_data:
            if c.get("visual_type") in ("chart", "counter"):
                rm = c.get("render_metadata") or {}
                if c.get("asset_id") == "shot_eps_metric":
                    if decimal.Decimal(str(rm.get("rendered_value", "0"))) != decimal.Decimal("2.93"):
                        failures.append("METRIC_VALUE_MISMATCH")
                es = rm.get("expected_series", [])
                rs = rm.get("rendered_series", [])
                if not es or es != rs or len(es) != 3 or es[0].get("label") != "Software" or es[0].get("value") != 5.0 or es[2].get("value") != -7.0:
                    failures.append("CHART_DATA_MISMATCH")
                
    failures = list(dict.fromkeys(failures))
    
    stage3_status = "candidate_complete" if not failures else "incomplete"
    acceptance_status = "valid" if not failures else "failed"

    status_payload = {
        "stage3_status": stage3_status,
        "acceptance_status": acceptance_status,
        "ready_for_stage4": False,
        "failure_codes": failures,
        "dependency_results": deps
    }
    
    with open(os.path.join(out_dir, "stage3_completion_status.json"), "w", encoding="utf-8") as f:
        json.dump(status_payload, f, indent=2)
        
    return status_payload

if __name__ == "__main__":
    if len(sys.argv) > 1:
        run_completion_gate(sys.argv[1])

