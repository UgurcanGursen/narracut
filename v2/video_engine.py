import os
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import (
    VideoFileClip, ImageClip, ColorClip, CompositeVideoClip, 
    TextClip, vfx, VideoClip
)
from moviepy.video.tools.subtitles import SubtitlesClip
from .models import VisualScene
from .canonical_payloads import CanonicalTextOverlayPayload, CanonicalMetricPayload

# Constants
TARGET_W, TARGET_H = 1920, 1080
FPS = 30
TEMP_DIR = os.path.join(os.getcwd(), "temp_assets")

def _ease_out_expo(x: float) -> float:
    return 1.0 if x == 1.0 else 1.0 - math.pow(2, -10 * x)

import uuid
import requests
import cv2

def _capture_autonomous_screenshot(url: str, target_text: str = "") -> tuple[str, list]:
    import hashlib
    import json
    import os
    from playwright.sync_api import sync_playwright
    
    os.makedirs(TEMP_DIR, exist_ok=True)
    identifier = hashlib.md5((url + str(target_text)).encode("utf-8")).hexdigest()
    img_path = os.path.join(TEMP_DIR, f"auto_scan_{identifier}.png")
    json_path = img_path.replace(".png", ".json")
    
    highlight_boxes = []
    
    if os.path.exists(img_path) and os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            highlight_boxes = json.load(f)
        return img_path, highlight_boxes
        
    try:
        with sync_playwright() as p:
            # Launch with anti-bot arguments
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-infobars",
                    "--window-size=1920,1080"
                ]
            )
            context = browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
                extra_http_headers={
                    "Accept-Language": "en-US,en;q=0.9",
                    "Sec-Fetch-Dest": "document",
                    "Sec-Fetch-Mode": "navigate",
                    "Sec-Fetch-Site": "none",
                    "Sec-Fetch-User": "?1",
                    "Upgrade-Insecure-Requests": "1"
                }
            )
            
            # Stealth Injection
            context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                window.chrome = {
                    runtime: {}
                };
            """)
            
            page = context.new_page()
            try:
                page.goto(url, wait_until="load", timeout=30000)
            except Exception:
                pass # ignore timeout and try to proceed
                
            page.wait_for_timeout(2000)
            
            # Ad-block & Cookie Banner Removal & Sticky Header Fix
            try:
                page.add_style_tag(content="""
                    iframe, ins, .ad, .ads, .advertisement, 
                    [id*='google_ads'], [id*='ad-'], [class*='ad-'],
                    [id*='cookie'], [class*='cookie'], #onetrust-consent-sdk,
                    [id*='popup'], [class*='popup'], [class*='newsletter'],
                    [id*='newsletter'], [class*='feedback'], [id*='feedback']
                    { display: none !important; }
                    header, nav, .header, .navbar, .sticky, [style*='position: fixed'], [style*='position: sticky'] {
                        position: relative !important;
                        height: auto !important;
                        min-height: 0 !important;
                    }
                """)
                page.evaluate("""
                    document.querySelectorAll('iframe, header, nav, [style*="position: fixed"], [style*="position: sticky"], [class*="sticky"], [id*="cookie"], [class*="cookie"], [class*="popup"]').forEach(el => {
                        el.style.position = 'relative'; 
                        if(el.id.includes('cookie') || el.className.includes('cookie')) el.remove();
                    });
                """)
            except:
                pass
                
            if target_text:
                js_find_rect = f"""
                (() => {{
                    const target = "{target_text.replace('"', '\\"')}";
                    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
                    let node;
                    while (node = walker.nextNode()) {{
                        if (node.nodeValue.includes(target)) {{
                            const range = document.createRange();
                            const idx = node.nodeValue.indexOf(target);
                            range.setStart(node, idx);
                            range.setEnd(node, idx + target.length);
                            
                            const span = document.createElement("span");
                            range.surroundContents(span);
                            span.scrollIntoView({{behavior: "instant", block: "center"}});
                            
                            const rect = span.getBoundingClientRect();
                            return [rect.x, rect.y, rect.width, rect.height];
                        }}
                    }}
                    return null;
                }})();
                """
                rect = page.evaluate(js_find_rect)
                if rect:
                    highlight_boxes = [rect]
                else:
                    page.evaluate("window.scrollTo(0, 0)")
            else:
                page.evaluate("window.scrollTo(0, 0)")
                
            page.wait_for_timeout(1000)
            page.screenshot(path=img_path, full_page=False)
            browser.close()
            
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(highlight_boxes, f)
    except Exception as e:
        print(f"  [AUTONOMOUS SCAN ERROR] Playwright failed: {e}")
        if not os.path.exists(img_path):
            Image.new("RGB", (TARGET_W, TARGET_H), (30, 30, 30)).save(img_path)
            
    return img_path, highlight_boxes

def process_document_scan(payload: dict, duration: float) -> VideoClip:
    url = payload.get("url", "")
    target_text = payload.get("target_text", "")
    
    img_path, highlight_boxes = _capture_autonomous_screenshot(url, target_text)
    
    pil_img = Image.open(img_path).convert("RGBA")
    box = highlight_boxes[0] if highlight_boxes else None
    
    def make_frame(t):
        frame_img = pil_img.copy()
        
        if box:
            x, y, w, h = [int(v) for v in box]
            dim_layer = Image.new("RGBA", frame_img.size, (0,0,0,150))
            draw_dim = ImageDraw.Draw(dim_layer)
            draw_dim.rectangle([x, y, x+w, y+h], fill=(0,0,0,0))
            frame_img = Image.alpha_composite(frame_img, dim_layer)
            
            marker_duration = 1.5
            progress = min(t / marker_duration, 1.0) if marker_duration > 0 else 1.0
            
            marker_layer = Image.new("RGBA", frame_img.size, (0,0,0,0))
            draw_marker = ImageDraw.Draw(marker_layer)
            marker_w = int(w * progress)
            draw_marker.rectangle([x, y, x+marker_w, y+h], fill=(255, 255, 0, 100))
            frame_img = Image.alpha_composite(frame_img, marker_layer)
            
        frame_img = frame_img.convert("RGB")
        
        scale = TARGET_W / frame_img.width
        new_h = int(frame_img.height * scale)
        if new_h < TARGET_H:
            scale = TARGET_H / frame_img.height
            new_w = int(frame_img.width * scale)
            frame_img = frame_img.resize((new_w, TARGET_H), Image.LANCZOS)
            final_img = Image.new("RGB", (TARGET_W, TARGET_H), (0,0,0))
            x_offset = (TARGET_W - new_w) // 2
            final_img.paste(frame_img, (x_offset, 0))
        else:
            frame_img = frame_img.resize((TARGET_W, new_h), Image.LANCZOS)
            final_img = Image.new("RGB", (TARGET_W, TARGET_H), (0,0,0))
            y_offset = (TARGET_H - new_h) // 2
            final_img.paste(frame_img, (0, y_offset))
            
        return np.array(final_img)
        
    clip = VideoClip(make_frame, duration=duration)
    
    def ken_burns(get_frame, t):
        frame = get_frame(t)
        scale = 1.0 + 0.05 * (t / max(duration, 0.1))
        h, w = frame.shape[:2]
        new_w, new_h = int(w * scale), int(h * scale)
        resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        cx = (new_w - w) // 2
        cy = (new_h - h) // 2
        return resized[cy:cy+h, cx:cx+w]
        
    return clip.fl(ken_burns)

def _create_pip_overlay(img_path: str, max_w: int, max_h: int) -> ImageClip:
    pil_img = Image.open(img_path).convert("RGBA")
    scale = min(max_w / pil_img.width, max_h / pil_img.height)
    new_w, new_h = int(pil_img.width * scale), int(pil_img.height * scale)
    pil_img = pil_img.resize((new_w, new_h), Image.LANCZOS)
    
    radius = 30
    mask = Image.new("L", (new_w, new_h), 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0, new_w, new_h), radius=radius, fill=255)
    pil_img.putalpha(mask)
    
    shadow_pad = 40
    shadow = Image.new("RGBA", (new_w + shadow_pad*2, new_h + shadow_pad*2), (0,0,0,0))
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_draw.rounded_rectangle((shadow_pad, shadow_pad, new_w + shadow_pad, new_h + shadow_pad), radius=radius, fill=(0,0,0,150))
    from PIL import ImageFilter
    shadow = shadow.filter(ImageFilter.GaussianBlur(15))
    
    shadow.paste(pil_img, (shadow_pad, shadow_pad), pil_img)
    
    tmp_path = os.path.join(TEMP_DIR, f"pip_overlay_{uuid.uuid4().hex[:8]}.png")
    shadow.save(tmp_path)
    return ImageClip(tmp_path)

def _get_pip_bg_clip(img_path: str, duration: float) -> VideoClip:
    pil_img = Image.open(img_path).convert("RGB")
    scale = max(TARGET_W / pil_img.width, TARGET_H / pil_img.height)
    new_w, new_h = int(pil_img.width * scale), int(pil_img.height * scale)
    pil_img = pil_img.resize((new_w, new_h), Image.LANCZOS)
    
    x = (new_w - TARGET_W) // 2
    y = (new_h - TARGET_H) // 2
    pil_img = pil_img.crop((x, y, x + TARGET_W, y + TARGET_H))
    
    from PIL import ImageFilter
    pil_img = pil_img.filter(ImageFilter.GaussianBlur(30))
    
    dim = Image.new("RGBA", pil_img.size, (0,0,0,100))
    pil_img = pil_img.convert("RGBA")
    pil_img = Image.alpha_composite(pil_img, dim).convert("RGB")
    
    tmp_path = os.path.join(TEMP_DIR, f"pip_bg_{uuid.uuid4().hex[:8]}.png")
    pil_img.save(tmp_path)
    return ImageClip(tmp_path).set_duration(duration)

def process_image_pip(payload: dict, duration: float) -> VideoClip:
    url = payload.get("url", "")
    image_url = payload.get("image_url", "")
    
    if url:
        target_text = payload.get("target_text", "")
        img_path, _ = _capture_autonomous_screenshot(url, target_text)
    else:
        ext = image_url.split('.')[-1].split('?')[0] if '.' in image_url else 'jpg'
        img_path = os.path.join(TEMP_DIR, f"pip_img_{uuid.uuid4().hex[:8]}.{ext}")
        
        os.makedirs(TEMP_DIR, exist_ok=True)
        if image_url.startswith("http"):
            res = requests.get(image_url, timeout=10)
            with open(img_path, "wb") as f:
                f.write(res.content)
        else:
            img_path = image_url
        
    bg_clip = _get_pip_bg_clip(img_path, duration)
    pip_clip = _create_pip_overlay(img_path, int(TARGET_W * 0.7), int(TARGET_H * 0.7))
    pip_clip = pip_clip.set_duration(duration).set_position('center')
    
    final_clip = CompositeVideoClip([bg_clip, pip_clip], size=(TARGET_W, TARGET_H)).set_duration(duration)
    
    def ken_burns_composite(get_frame, t):
        frame = get_frame(t)
        scale = 1.0 + 0.05 * (t / max(duration, 0.1))
        h, w = frame.shape[:2]
        new_w, new_h = int(w * scale), int(h * scale)
        resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        cx = (new_w - w) // 2
        cy = (new_h - h) // 2
        return resized[cy:cy+h, cx:cx+w]
        
    return final_clip.fl(ken_burns_composite)

def make_black_clip(duration: float) -> ColorClip:
    return ColorClip(size=(TARGET_W, TARGET_H), color=(0,0,0), duration=duration)

def create_animated_fallback_clip(duration: float, visual_type: str = "Unknown", reason: str = "Asset Unavailable") -> VideoClip:
    img = Image.new("RGB", (TARGET_W, TARGET_H), (20, 20, 25))
    draw = ImageDraw.Draw(img)
    font_main = _get_pil_font(80, bold=True)
    font_sub = _get_pil_font(40)
    
    t_main = f"VISUAL UNAVAILABLE ({visual_type.upper()})"
    bbox = draw.textbbox((0, 0), t_main, font=font_main)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((TARGET_W-tw)/2, (TARGET_H-th)/2 - 50), t_main, font=font_main, fill=(255,100,100))
    
    bbox = draw.textbbox((0, 0), reason, font=font_sub)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((TARGET_W-tw)/2, (TARGET_H-th)/2 + 50), reason, font=font_sub, fill=(180,180,180))
    
    img_path = os.path.join(TEMP_DIR, f"fallback_{visual_type}.png")
    img.save(img_path)
    
    return ImageClip(img_path).set_duration(duration)

def fit_video_clip(clip: VideoClip, fit_mode: str = "cover") -> VideoClip:
    raise NotImplementedError("fit_video_clip is deprecated! Use normalize_video_asset from normalizer.py instead.")

def _get_pil_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    # Use standard Arial, fallback to default if not found
    try:
        font_name = "arialbd.ttf" if bold else "arial.ttf"
        return ImageFont.truetype(font_name, size)
    except IOError:
        return ImageFont.load_default()

def process_big_text(payload: CanonicalTextOverlayPayload, duration: float) -> VideoClip:
    img_path = os.path.join(TEMP_DIR, f"big_text_{payload.main_text[:10] if payload.main_text else 'x'}.png")
    img = Image.new("RGBA", (TARGET_W, TARGET_H), (10, 15, 30, 255))
    draw = ImageDraw.Draw(img)
    
    # Modern Subtle Radial Gradient (Dark Navy)
    for r in range(TARGET_W, 0, -100):
        color_val = max(10, 30 - int(20 * (r / TARGET_W)))
        draw.ellipse([(TARGET_W//2 - r, TARGET_H//2 - r), (TARGET_W//2 + r, TARGET_H//2 + r)], fill=(color_val, color_val+5, color_val+15, 255))

    
    def draw_wrapped_text(text, max_width, initial_font_size, fill_color, is_bold, offset_y):
        font_size = initial_font_size
        lines = []
        font = None
        while font_size > 30:
            font = _get_pil_font(font_size, bold=is_bold)
            words = text.split()
            lines = []
            line = ""
            for w in words:
                test = line + " " + w if line else w
                if draw.textbbox((0,0), test, font=font)[2] > max_width:
                    if line: lines.append(line)
                    line = w
                else:
                    line = test
            if line: lines.append(line)
            
            total_h = len(lines) * (font_size + 10)
            if total_h < TARGET_H - 180:
                break
            font_size -= 10
            
        total_h = len(lines) * (font_size + 10)
        y = (TARGET_H - total_h) / 2 + offset_y
        
        for l in lines:
            bbox = draw.textbbox((0,0), l, font=font)
            x = (TARGET_W - (bbox[2]-bbox[0])) / 2
            draw.text((x, y), l, font=font, fill=fill_color)
            y += font_size + 10
            
    if payload.main_text:
        offset = -100 if payload.sub_text else 0
        draw_wrapped_text(payload.main_text, TARGET_W * 0.85, 120, (255,255,255), True, offset)
        
    if payload.sub_text:
        draw_wrapped_text(payload.sub_text, TARGET_W * 0.85, 60, (180,180,180), False, 150)
        
    img = img.convert("RGB")
    
    base_clip = ImageClip(np.array(img)).set_duration(duration)
    # Professional Slow Zoom (1.0 -> 1.05)
    def resize_func(t):
        return 1.0 + 0.05 * (t / duration)
    return base_clip.resize(resize_func).crop(x_center=TARGET_W/2, y_center=TARGET_H/2, width=TARGET_W, height=TARGET_H)

def process_counter(payload: CanonicalMetricPayload, duration: float) -> VideoClip:
    start_v = payload.start_val
    end_v = payload.end_val
    prefix = payload.prefix
    suffix = payload.suffix
    label = payload.label
    decimals = payload.decimal_places
    
    from .config import ENABLE_COUNTER
    if not ENABLE_COUNTER:
        fmt = f"{{:.{decimals}f}}"
        start_str = f"{prefix}{fmt.format(start_v)}{suffix}"
        end_str = f"{prefix}{fmt.format(end_v)}{suffix}"
        main_txt = f"{start_str} → {end_str}"
        
        # Fallback to big_text
        text_payload = CanonicalTextOverlayPayload(main_text=main_txt, sub_text=label)
        return process_big_text(text_payload, duration)
        
    def make_frame(t):
        progress = t / duration
        eased = _ease_out_expo(progress)
        current_val = start_v + (end_v - start_v) * eased
        
        img = Image.new("RGB", (TARGET_W, TARGET_H), (15, 15, 15))
        draw = ImageDraw.Draw(img)
        
        font_val = _get_pil_font(200, bold=True)
        font_label = _get_pil_font(70)
        
        val_str = f"{current_val:.{decimals}f}"
        val_text = f"{prefix}{val_str}{suffix}"
        
        bbox = draw.textbbox((0, 0), val_text, font=font_val)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text(((TARGET_W-tw)/2, (TARGET_H-th)/2 - 50), val_text, font=font_val, fill=(255, 100, 100))
        
        if label:
            bbox = draw.textbbox((0, 0), label, font=font_label)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
            draw.text(((TARGET_W-tw)/2, (TARGET_H-th)/2 + 120), label, font=font_label, fill=(200, 200, 200))
            
        return np.array(img)
        
    clip = VideoClip(make_frame, duration=duration)
    clip.render_metadata = {
        "expected_value": str(end_v),
        "rendered_value": str(end_v),
        "precision": decimals,
        "prefix": prefix,
        "suffix": suffix,
        "animation_type": "count_up",
        "animation_completed": True
    }
    return clip

def process_web_record_clip(image_path: str, duration: float, scroll_duration: float = 2.0) -> VideoClip:
    if not image_path or not os.path.exists(image_path):
        return make_black_clip(duration)
        
    pil_img = Image.open(image_path).convert("RGB")
    scale = TARGET_W / pil_img.width
    new_w = TARGET_W
    new_h = int(math.ceil(pil_img.height * scale))
    pil_img = pil_img.resize((new_w, new_h), Image.LANCZOS)
    
    # Save resized temp
    rs_path = image_path.replace(".png", "_resized.png")
    pil_img.save(rs_path)
    
    base_clip = ImageClip(rs_path).set_duration(duration)
    
    max_scroll = max(0, new_h - TARGET_H)
    
    def scroll_filter(get_frame, t):
        if t <= 0.5:
            y = 0
        elif t >= duration - 0.5:
            y = max_scroll
        else:
            progress = (t - 0.5) / (duration - 1.0)
            eased = _ease_out_expo(progress)
            y = int(max_scroll * eased)
            
        frame = get_frame(t)
        return frame[y:y+TARGET_H, 0:TARGET_W]
        
    return base_clip.fl(scroll_filter)


    
def slice_alignment(align_data: list, start_time: float, end_time: float) -> list:
    """
    Slices Whisper transcription words based on start_time and end_time.
    Normalizes timestamps so the first word starts relative to 0.0.
    """
    sliced = []
    for item in align_data:
        word_start = item["start"]
        word_end = item["end"]
        mid = (word_start + word_end) / 2.0
        
        if start_time <= mid <= end_time:
            new_start = max(0.0, word_start - start_time)
            new_end = max(0.0, word_end - start_time)
            sliced.append({
                "start": new_start,
                "end": new_end,
                "word": item["word"]
            })
    return sliced

def generate_subtitles(words_data: list, clip_duration: float, scene_type: str) -> list:
    """
    words_data is from audio_engine Whisper alignment.
    Returns list of tuples: ((start_t, end_t), "Subtitle text")
    """
    # Group words into 2-line chunks (max ~42 chars)
    subs = []
    current_line = ""
    start_t = 0
    end_t = 0
    
    for item in words_data:
        word = item["word"]
        
        if not current_line:
            start_t = item["start"]
            current_line = word
            end_t = item["end"]
        else:
            if len(current_line) + len(word) > 42:
                subs.append(((start_t, end_t), current_line))
                start_t = item["start"]
                current_line = word
                end_t = item["end"]
            else:
                current_line += " " + word
                end_t = item["end"]
                
    if current_line:
        subs.append(((start_t, min(end_t, clip_duration)), current_line))
        
    return subs

def add_subtitles_to_clip(base_clip: VideoClip, subs: list, scene_type: str) -> VideoClip:
    if not subs:
        return base_clip
        
    def text_generator(txt):
        font = _get_pil_font(48, bold=True)
        dummy = Image.new("RGBA", (10, 10))
        d_draw = ImageDraw.Draw(dummy)
        bbox = d_draw.textbbox((0,0), txt, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        
        pad_x = 24
        pad_y = 12
        img = Image.new("RGBA", (tw + pad_x*2, th + pad_y*2), (0,0,0,0))
        draw = ImageDraw.Draw(img)
        
        # Dark translucent background box
        draw.rectangle([0, 0, img.width, img.height], fill=(0, 0, 0, 180))
        
        # Main text (no stroke)
        draw.text((pad_x, pad_y - 2), txt, font=font, fill=(255, 255, 255, 255))
        
        return ImageClip(np.array(img))
                                     
    sub_clip = SubtitlesClip(subs, text_generator)
    
    # Safe area placement (V3)
    sub_clip = sub_clip.set_position(('center', TARGET_H - 180))
        
    return CompositeVideoClip([base_clip, sub_clip])
def generate_local_transition(clip_a: VideoClip, clip_b: VideoClip, duration: float = 0.15, transition_type: str = "short_dissolve") -> VideoClip:
    if transition_type != "short_dissolve": return None
    import hashlib
    import numpy as np
    from moviepy.editor import ImageSequenceClip
    
    fp_a = getattr(clip_a, "filename", str(id(clip_a)))
    fp_b = getattr(clip_b, "filename", str(id(clip_b)))
    
    hash_str = f"{fp_a}_{fp_b}_{duration}_{TARGET_W}_{TARGET_H}_{FPS}_V2.3.1_safeblend"
    cache_key = hashlib.md5(hash_str.encode('utf-8')).hexdigest()
    
    from .cache_manager import CACHE_BASE
    trans_path = os.path.join(CACHE_BASE, "transitions", f"trans_{cache_key}.mp4")
    
    if os.path.exists(trans_path):
        from moviepy.editor import VideoFileClip
        return VideoFileClip(trans_path)
        
    os.makedirs(os.path.dirname(trans_path), exist_ok=True)
    
    # Safe frame extraction
    def get_safe_frames(clip, start_t, dur, fps):
        frames = []
        n_needed = max(1, int(dur * fps))
        for i in range(n_needed):
            t = start_t + (i / fps)
            # Prevent exact EOF overflow by capping t just slightly below duration
            t = min(t, max(0, clip.duration - 0.01))
            try:
                frame = clip.get_frame(t)
                frames.append(frame)
            except Exception:
                # If error (EOF or ffmpeg read fail), duplicate last frame or use black
                if frames:
                    frames.append(frames[-1])
                else:
                    frames.append(np.zeros((TARGET_H, TARGET_W, 3), dtype=np.uint8))
        return frames

    # Extract exactly N frames for A (end) and B (start)
    start_t_a = max(0.0, clip_a.duration - duration)
    start_t_b = 0.0
    
    frames_a = get_safe_frames(clip_a, start_t_a, duration, FPS)
    frames_b = get_safe_frames(clip_b, start_t_b, duration, FPS)
    
    n_frames = min(len(frames_a), len(frames_b))
    if n_frames == 0:
        return None
        
    blended_frames = []
    for i in range(n_frames):
        alpha = (i + 1) / (n_frames + 1)
        img_a = frames_a[i].astype(np.float32)
        img_b = frames_b[i].astype(np.float32)
        blended = (img_a * (1.0 - alpha) + img_b * alpha).astype(np.uint8)
        blended_frames.append(blended)
        
    # Write to MP4 using ImageSequenceClip
    seq_clip = ImageSequenceClip(blended_frames, fps=FPS)
    print(f"  [INFO] Generating robust local transition: {transition_type} ({duration}s)...")
    seq_clip.write_videofile(trans_path, fps=FPS, codec="libx264", audio=False, preset="ultrafast", logger=None)
    
    from moviepy.editor import VideoFileClip
    return VideoFileClip(trans_path)
