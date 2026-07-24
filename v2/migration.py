import json
import os
from .models import TimelineV2, convert_v1_to_v2, TimelineV2_3, EditorialBeat, EditorialShot

def convert_to_editorial(file_path: str) -> tuple:
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    format_type = "v2"
    if isinstance(data, list):
        format_type = "v2_blocks_list"
        if len(data) > 0 and "narration" in data[0] and "visuals" not in data[0]:
            format_type = "v1"
    
    if format_type == "v1":
        legacy_timeline = convert_v1_to_v2(data)
    else:
        known_visual_fields = {
            "offset_start", "offset_end", "type", "clip_start", "clip_end", "query", "url", "target_text", "target_selector", 
            "zoom", "scroll_duration", "highlight_target", "main_text", "sub_text", "background_style", "accent_animation", 
            "logo_url", "start_val", "end_val", "prefix", "suffix", "label", "is_approximate", "max_height", "crop_mode", 
            "fit_mode", "extra", "narration_cue_start", "narration_cue_end", "visual_purpose", "required_content", 
            "forbidden_content", "fallback_queries", "allow_generic_stock", "transition_in", "transition_out", "subtitle_policy", 
            "fill_policy", "asset_locked", "selected_asset_url", "sfx_category"
        }
        
        blocks = data if format_type == "v2_blocks_list" else data.get("blocks", [])
        for b in blocks:
            for v in b.get("visuals", []):
                extra_dict = v.get("extra", {})
                keys_to_del = []
                for k, val in v.items():
                    if k not in known_visual_fields:
                        extra_dict[k] = val
                        keys_to_del.append(k)
                for k in keys_to_del:
                    del v[k]
                v["extra"] = extra_dict
                
        legacy_timeline = TimelineV2(blocks=blocks)
        
    beats = []
    
    report = {
        "source_schema": format_type,
        "target_schema": "2.3-editorial",
        "converted_shots": 0,
        "review_required_shots": 0,
        "missing_visual_purpose": 0,
        "missing_trigger_cue": 0,
        "legacy_locked_timing": 0
    }
    
    for block in legacy_timeline.blocks:
        shots = []
        for v in block.visuals:
            # Guessing fields
            missing_purpose = not bool(v.visual_purpose)
            missing_trigger = not bool(v.trigger_cue and v.trigger_cue.strip()) and not bool(v.narration_cue_start)
            
            shot_role = v.extra.get("shot_role", "illustrate") if isinstance(v.extra, dict) else "illustrate"
            vis_purpose = v.visual_purpose if not missing_purpose else "MIGRATION_REVIEW_REQUIRED"
            timing = getattr(v, "timing_mode", "legacy_locked")
            if timing not in ["cue_anchor", "cue_locked", "legacy_locked"]:
                timing = "legacy_locked"
                
            trigger = v.trigger_cue or v.narration_cue_start or "MISSING_TRIGGER"
            
            # Identify required review
            review_status = "auto_approved_trusted"
            if v.type in ["stock", "youtube", "web_record"] or missing_purpose or trigger == "MISSING_TRIGGER":
                review_status = "review_required"
                
            # Map legacy flat fields into canonical payload
            payload_dict = v.extra if isinstance(v.extra, dict) else {}
            
            legacy_flat_fields = [
                "start_val", "end_val", "prefix", "suffix", "label", "decimal_places",
                "source", "headline", "content_before", "main_text", "sub_text",
                "query", "target_selector", "chart_title", "x_labels", "y_values", "chart_type",
                "value_suffix", "source_note", "illustrative", "text", "author", "title"
            ]
            for field in legacy_flat_fields:
                val = getattr(v, field, None)
                if val is not None and field not in payload_dict:
                    payload_dict[field] = val
                    
            if v.url and "source_url" not in payload_dict:
                payload_dict["source_url"] = v.url
                    
            # Map target_text if present in V2 visual but not in payload
            if v.target_text and "target_text" not in payload_dict:
                payload_dict["target_text"] = v.target_text
                
            shot = EditorialShot(
                trigger_cue=trigger,
                shot_role=shot_role,
                visual_type=v.type,
                visual_purpose=vis_purpose,
                timing_mode=timing,
                review_status=review_status,
                query=v.query,
                url=v.url,
                target_text=v.target_text,
                target_selector=v.target_selector,
                clip_start=v.clip_start,
                clip_end=v.clip_end,
                crop_mode=v.crop_mode or "none",
                fit_mode=v.fit_mode,
                transition_in=v.transition_in or "hard_cut",
                payload=payload_dict
            )
            shots.append(shot)
            
            report["converted_shots"] += 1
            if review_status == "review_required":
                report["review_required_shots"] += 1
            if missing_purpose:
                report["missing_visual_purpose"] += 1
            if trigger == "MISSING_TRIGGER":
                report["missing_trigger_cue"] += 1
            if timing == "legacy_locked":
                report["legacy_locked_timing"] += 1
                
        beat = EditorialBeat(
            narration_text=block.narration,
            shots=shots
        )
        beats.append(beat)
        
    timeline_v3 = TimelineV2_3(beats=beats)
    
    # Save the migrated JSON
    base_name = os.path.basename(file_path).replace(".json", "")
    out_path = os.path.join(os.path.dirname(file_path) or ".", "output", f"migrated_{base_name}_v2_3.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(timeline_v3.model_dump_json(indent=2))
        
    rep_path = os.path.join(os.path.dirname(file_path) or ".", "output", "migration_report.json")
    with open(rep_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
        
    return timeline_v3, report, out_path
