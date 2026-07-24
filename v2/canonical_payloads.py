"""
Canonical Payload Models for V3 Editorial Engine.

Her görsel türü için typed, doğrulanabilir payload modeli.
Renderer'lar doğrudan bu modelleri alır. extra dict veya VisualScene bağımlılığı yoktur.
"""
import re
from typing import List, Optional
from pydantic import BaseModel, Field, validator


# ─── Ortak Doğrulama Yardımcıları ────────────────────────────────────────────

_FORBIDDEN_PLACEHOLDERS = [
    "chart data", "chart title", "unknown", "placeholder",
    "quote text", "quote text missing", "news report",
    "breaking news", "content highlighted here",
    "visual unavailable", "article requires", "chart requires",
]

def _reject_placeholder(value: str, field_name: str) -> str:
    """Boş veya placeholder string'leri reddet."""
    if not value or not value.strip():
        raise ValueError(f"{field_name} boş olamaz")
    if value.strip().lower() in _FORBIDDEN_PLACEHOLDERS:
        raise ValueError(f"{field_name} placeholder değer içeriyor: '{value}'")
    return value


# ─── Stock ────────────────────────────────────────────────────────────────────

class CanonicalStockPayload(BaseModel):
    query: Optional[str] = ""
    fallback_queries: List[str] = Field(default_factory=list)
    allow_generic_stock: bool = True
    visual_purpose: str = ""
    required_content: List[str] = Field(default_factory=list)
    forbidden_content: List[str] = Field(default_factory=list)
    fit_mode: str = "cover"
    asset_mode: str = "auto"
    asset_id: str = ""
    resolved_path: str = ""

    @validator("query")
    def query_not_empty(cls, v, values):
        if values.get("asset_mode") == "locked_local":
            return v
        return _reject_placeholder(v, "query")


# ─── Source (web_record) ──────────────────────────────────────────────────────

class CanonicalSourcePayload(BaseModel):
    source_url: str
    target_text: str
    target_selector: str = ""
    zoom: float = 1.7
    highlight_target: bool = True
    scroll_duration: float = 1.2

    @validator("source_url")
    def url_not_empty(cls, v):
        return _reject_placeholder(v, "source_url")

    @validator("target_text")
    def text_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("SOURCE_TARGET_TEXT_MISSING")
        if v.strip().lower() in _FORBIDDEN_PLACEHOLDERS:
            raise ValueError("SOURCE_TARGET_TEXT_MISSING")
        return v


# ─── Chart ────────────────────────────────────────────────────────────────────

class CanonicalChartPayload(BaseModel):
    chart_title: str
    x_labels: List[str]
    y_values: List[float]
    chart_type: str = "bar"
    value_suffix: str = ""
    source_note: str = ""
    source_url: str = ""
    illustrative: bool = False

    @validator("chart_title")
    def title_valid(cls, v):
        return _reject_placeholder(v, "chart_title")

    @validator("x_labels")
    def labels_not_empty(cls, v):
        if not v:
            raise ValueError("x_labels boş olamaz")
        return v

    @validator("y_values")
    def values_not_empty(cls, v):
        if not v:
            raise ValueError("y_values boş olamaz")
        return v


# ─── Metric (counter) ────────────────────────────────────────────────────────

class CanonicalMetricPayload(BaseModel):
    start_val: float
    end_val: float
    label: str
    prefix: str = ""
    suffix: str = ""
    decimal_places: int = 0
    percentage_change: Optional[str] = None
    source_note: str = ""
    source_url: str = ""

    @validator("label")
    def label_valid(cls, v):
        return _reject_placeholder(v, "label")

    @validator("end_val")
    def vals_not_both_zero(cls, v, values):
        start = values.get("start_val", 0)
        if start == 0 and v == 0:
            raise ValueError("METRIC 0 → 0 üretmek yasaktır. start_val ve end_val ikisi birden 0 olamaz.")
        return v


# ─── Article (highlight_article) ─────────────────────────────────────────────

class CanonicalArticlePayload(BaseModel):
    source: str
    headline: str
    target_text: str
    content_before: str = ""
    source_url: str = ""

    @validator("source")
    def source_valid(cls, v):
        return _reject_placeholder(v, "source")

    @validator("headline")
    def headline_valid(cls, v):
        return _reject_placeholder(v, "headline")

    @validator("target_text")
    def target_valid(cls, v):
        return _reject_placeholder(v, "target_text")


# ─── Text Overlay (big_text) ─────────────────────────────────────────────────

class CanonicalTextOverlayPayload(BaseModel):
    main_text: str
    eyebrow: str = ""
    sub_text: str = ""
    source_label: str = ""
    accent_text: str = ""

    @validator("main_text")
    def main_valid(cls, v):
        return _reject_placeholder(v, "main_text")


# ─── Quote ────────────────────────────────────────────────────────────────────

class CanonicalQuotePayload(BaseModel):
    text: str
    author: str
    title: str = ""
    source_url: str = ""

    @validator("text")
    def text_valid(cls, v):
        return _reject_placeholder(v, "text")

    @validator("author")
    def author_valid(cls, v):
        return _reject_placeholder(v, "author")


# ─── Motion (gelecek fazlar için) ────────────────────────────────────────────

class CanonicalMotionPayload(BaseModel):
    """Gelecek motion template'leri için placeholder model."""
    template_name: str = ""
    base_asset: Optional[str] = None
    overlays: List[dict] = Field(default_factory=list)


# ─── Payload Resolution ──────────────────────────────────────────────────────

PAYLOAD_TYPE_MAP = {
    "stock": CanonicalStockPayload,
    "web_record": CanonicalSourcePayload,
    "chart": CanonicalChartPayload,
    "counter": CanonicalMetricPayload,
    "highlight_article": CanonicalArticlePayload,
    "big_text": CanonicalTextOverlayPayload,
    "quote": CanonicalQuotePayload,
}


class CanonicalPayloadInvalid(Exception):
    """Canonical payload doğrulaması başarısız olduğunda fırlatılır."""
    def __init__(self, visual_type: str, shot_id: str, errors: str):
        self.visual_type = visual_type
        self.shot_id = shot_id
        self.errors = errors
        super().__init__(f"CANONICAL_PAYLOAD_INVALID [{visual_type}] shot={shot_id}: {errors}")


def resolve_canonical_payload(visual_type: str, payload_dict: dict, shot_id: str = ""):
    """
    visual_type'a göre doğru canonical payload modelini seçer,
    payload_dict'i parse eder ve doğrular.
    
    Başarısız olursa CanonicalPayloadInvalid fırlatır.
    
    Returns:
        Parsed canonical payload model instance
    """
    payload_cls = PAYLOAD_TYPE_MAP.get(visual_type)
    
    if payload_cls is None:
        # Bilinmeyen türler (black, youtube, reddit vb.) için payload validation atlanır
        return payload_dict
    
    try:
        return payload_cls(**payload_dict)
    except Exception as e:
        raise CanonicalPayloadInvalid(visual_type, shot_id, str(e))
