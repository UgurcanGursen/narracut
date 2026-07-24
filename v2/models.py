import json
import uuid
from typing import List, Optional, Union, Dict, Any
from pydantic import BaseModel, Field

class SfxConfig(BaseModel):
    enabled: bool = False
    asset_id: Optional[str] = None
    trigger_cue: Optional[str] = None
    gain_db: float = 0.0
    max_duration: Optional[float] = None

class BgmConfig(BaseModel):
    enabled: bool = False
    track_id: Optional[str] = None
    gain_db: float = -22.0
    fade_in: float = 0.0
    fade_out: float = 0.0

class VisualScene(BaseModel):
    offset_start: Union[float, str] = 0.0  # Can be "AUTO"
    offset_end: Union[float, str] = "AUTO" 
    type: str
    
    # Generic fields that map to various modules
    clip_start: float = 0.0
    clip_end: float = 0.0
    query: Optional[str] = None
    url: Optional[str] = None
    
    # Web Record fields
    target_text: Optional[str] = None
    target_selector: Optional[str] = None
    zoom: float = 1.7
    scroll_duration: float = 2.0
    highlight_target: bool = True
    
    # Big Text fields
    main_text: Optional[str] = None
    sub_text: Optional[str] = None
    background_style: str = "black"
    accent_animation: str = "impact"
    logo_url: Optional[str] = None
    
    # Counter fields
    start_val: Optional[float] = None
    end_val: Optional[float] = None
    prefix: Optional[str] = ""
    suffix: Optional[str] = ""
    label: Optional[str] = None
    is_approximate: bool = False
    
    # New fields
    max_height: Optional[int] = None
    crop_mode: Optional[str] = "none"
    fit_mode: Optional[str] = None
    
    # Generic passthrough for anything else
    extra: Dict[str, Any] = Field(default_factory=dict)
    
    # V2.2 Editorial Fields
    narration_cue_start: Optional[str] = None
    narration_cue_end: Optional[str] = None
    visual_purpose: Optional[str] = None
    required_content: Optional[List[str]] = Field(default_factory=list)
    forbidden_content: Optional[List[str]] = Field(default_factory=list)
    fallback_queries: Optional[List[str]] = Field(default_factory=list)
    allow_generic_stock: bool = True
    transition_in: Optional[str] = None
    transition_out: Optional[str] = None
    
    # V2.4 Architecture Fields
    timing_mode: Optional[str] = None # e.g. "cue_anchor"
    trigger_cue: Optional[str] = None
    min_duration: Optional[float] = None
    max_duration: Optional[float] = 15.0
    subtitle_policy: str = "hide_tool_subtitles"
    fill_policy: str = "error"
    asset_locked: bool = False
    selected_asset_url: Optional[str] = None
    sfx_category: Optional[str] = None
    
    # V2.3 Synchronization & Audio
    timing_mode: str = "cue_locked"
    preferred_duration: Optional[float] = None
    min_duration: Optional[float] = None
    max_duration: Optional[float] = None
    sfx: Optional[SfxConfig] = None
    
class NarrationBlock(BaseModel):
    block_id: str = Field(default_factory=lambda: f"block_{uuid.uuid4().hex[:8]}")
    narration: str = ""
    audio_file: Optional[str] = None
    pause_before: float = 0.3
    pause_after: float = 0.5
    bgm_drop: bool = False
    sfx_category: Optional[str] = None
    fill_policy: str = "error"
    visuals: List[VisualScene] = Field(default_factory=list)

class TimelineV2(BaseModel):
    bgm: Optional[BgmConfig] = None
    blocks: List[NarrationBlock]

def convert_v1_to_v2(v1_data: List[dict]) -> TimelineV2:
    """
    Converts old V1 timeline JSON format (one visual per block) 
    into the new TimelineV2 architecture where one narration can have multiple visuals.
    """
    blocks_v2 = []
    
    for idx, item in enumerate(v1_data):
        # Determine block_id
        block_id = item.get("block_id", f"auto_block_{idx:03d}")
        
        # Narration fields
        narration = item.get("narration", "")
        pause_before = float(item.get("pause_before", 0.5))
        pause_after = float(item.get("pause_after", 0.5))
        bgm_drop = bool(item.get("bgm_drop", False))
        
        # Visual fields
        vis_type = item.get("type", "stock")
        visual = VisualScene(
            offset_start=0.0,
            offset_end="AUTO",
            type=vis_type
        )
        
        # Map known fields
        for k, v in item.items():
            if k in ["narration", "pause_before", "pause_after", "bgm_drop", "block_id", "type"]:
                continue
            
            if hasattr(visual, k):
                setattr(visual, k, v)
            else:
                visual.extra[k] = v
                
        # Build block
        nb = NarrationBlock(
            block_id=block_id,
            narration=narration,
            pause_before=pause_before,
            pause_after=pause_after,
            bgm_drop=bgm_drop,
            visuals=[visual]
        )
        blocks_v2.append(nb)
        
    return TimelineV2(blocks=blocks_v2)


class TimelineValidator:
    def __init__(self):
        self.errors = []
        self.warnings = []
        
    def validate(self, timeline: TimelineV2):
        self.errors = []
        self.warnings = []
        
        for idx, block in enumerate(timeline.blocks):
            if not block.narration.strip():
                self.warnings.append(f"Block '{block.block_id}' has empty narration.")
                
            if block.pause_before < 0 or block.pause_after < 0:
                self.errors.append(f"Block '{block.block_id}' has negative pauses.")
                
            prev_end = 0.0
            for v_idx, vis in enumerate(block.visuals):
                if isinstance(vis.offset_start, float) and isinstance(vis.offset_end, float):
                    if vis.offset_start >= vis.offset_end:
                        self.errors.append(f"Block '{block.block_id}', Visual {v_idx}: start >= end.")
                    
                    if vis.offset_start > prev_end:
                        self.warnings.append(f"Block '{block.block_id}': Gap detected between visuals at {prev_end} and {vis.offset_start}.")
                    
                    if vis.offset_start < prev_end:
                        self.errors.append(f"Block '{block.block_id}': Visual {v_idx} overlaps with previous visual.")
                        
                    prev_end = vis.offset_end
                
                # Check required payload for explicit text scenes
                if vis.type == "chart":
                    title = vis.extra.get("chart_title")
                    x = vis.extra.get("x_labels")
                    y = vis.extra.get("y_values")
                    if not title or title == "Chart Data" or not x or not y:
                        self.errors.append(f"Block '{block.block_id}', Visual {v_idx}: chart requires real chart_title, x_labels, and y_values")
                
                if vis.type == "quote":
                    text = vis.extra.get("text", vis.extra.get("quote"))
                    name = vis.extra.get("name", vis.extra.get("author"))
                    if not text or text == "Quote text missing" or text == "Quote text" or not name or name == "Unknown":
                        self.errors.append(f"Block '{block.block_id}', Visual {v_idx}: quote requires real name and text")
                        
                if vis.type == "highlight_article":
                    src = vis.extra.get("source")
                    hl = vis.extra.get("headline")
                    tt = vis.target_text if getattr(vis, "target_text", None) else vis.extra.get("target_text")
                    if not src or src == "NEWS REPORT" or not hl or hl == "Breaking News" or not tt or tt == "Content highlighted here":
                        self.errors.append(f"Block '{block.block_id}', Visual {v_idx}: highlight_article requires real source, headline, and target_text")
                
                if vis.type == "web_record" and not vis.target_text and not vis.target_selector:
                    self.warnings.append(f"Block '{block.block_id}': 'web_record' missing target_text/selector, will just scroll blindly.")
                    
                if vis.type == "youtube":
                    if vis.clip_end <= vis.clip_start:
                        self.errors.append(f"Block '{block.block_id}', Visual {v_idx}: clip_end ({vis.clip_end}) must be greater than clip_start ({vis.clip_start}).")
        
        return {
            "is_valid": len(self.errors) == 0,
            "errors": self.errors,
            "warnings": self.warnings
        }

# ==========================================
# V3 Editorial Documentary Models
# ==========================================

class EditorialShot(BaseModel):
    shot_id: str = Field(default_factory=lambda: f"shot_{uuid.uuid4().hex[:8]}")
    trigger_cue: str
    preferred_duration: Optional[float] = None
    min_duration: Optional[float] = None
    max_duration: Optional[float] = None
    shot_role: str = "illustrate"  # establish, evidence, explain, reinforce, contrast, reaction, transition, payoff
    visual_type: str
    visual_purpose: str = ""
    motion_template: Optional[str] = None
    transition_in: str = "hard_cut"
    timing_mode: str = "cue_anchor"
    review_status: str = "auto_approved_trusted" # review_required, approved, rejected, locked
    
    # Generic fields (compatible with legacy)
    query: Optional[str] = None
    url: Optional[str] = None
    target_text: Optional[str] = None
    target_selector: Optional[str] = None
    clip_start: float = 0.0
    clip_end: float = 0.0
    crop_mode: str = "none"
    fit_mode: Optional[str] = None
    
    resolved_asset_path: Optional[str] = None
    content_fingerprint: Optional[str] = None
    
    payload: Dict[str, Any] = Field(default_factory=dict)
    
class EditorialBeat(BaseModel):
    beat_id: str = Field(default_factory=lambda: f"beat_{uuid.uuid4().hex[:8]}")
    narration_start_cue: Optional[str] = None
    narration_end_cue: Optional[str] = None
    narration_text: str = ""
    purpose: Optional[str] = None
    claim_type: Optional[str] = None
    source_requirement: Optional[str] = None
    shots: List[EditorialShot] = Field(default_factory=list)

class TimelineV2_3(BaseModel):
    bgm: Optional[BgmConfig] = None
    beats: List[EditorialBeat]

class EditorialValidator:
    MIN_DURATIONS = {
        "stock": 1.8,
        "web_record": 2.5,
        "chart": 3.5,
        "counter": 2.5,
        "quote": 3.0,
        "highlight_article": 2.5,
        "big_text": 1.2,
        "black": 0.5,
    }

    def __init__(self):
        self.errors = []
        self.warnings = []
        
    def validate(self, timeline: TimelineV2_3):
        self.errors = []
        self.warnings = []
        
        all_shots = []
        roles = set()
        
        for beat in timeline.beats:
            for shot in beat.shots:
                all_shots.append(shot)
                roles.add(shot.shot_role)
                
                type_min = self.MIN_DURATIONS.get(shot.visual_type, 1.8)
                if shot.min_duration is not None and shot.min_duration < type_min:
                    self.errors.append(f"Shot '{shot.shot_id}' min_duration {shot.min_duration} is below type minimum {type_min}.")
                
                if shot.preferred_duration is not None and shot.preferred_duration < type_min:
                    self.errors.append(f"Shot '{shot.shot_id}' preferred_duration {shot.preferred_duration} is below type minimum {type_min}.")

        if len(roles) < 2:
            self.errors.append(f"Editorial standard failed: Minimum 2 different shot roles required, found {len(roles)}.")
            
        for i in range(1, len(all_shots)):
            if all_shots[i].shot_id == all_shots[i-1].shot_id:
                self.errors.append(f"Duplicate consecutive shot_id found: '{all_shots[i].shot_id}'.")
                
        return {
            "is_valid": len(self.errors) == 0,
            "errors": self.errors,
            "warnings": self.warnings
        }
