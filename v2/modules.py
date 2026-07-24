import os
import math
from typing import Tuple
from PIL import Image, ImageDraw
import numpy as np
import hashlib
from moviepy.editor import VideoClip, ImageClip

from .models import VisualScene
from .canonical_payloads import CanonicalChartPayload, CanonicalQuotePayload, CanonicalArticlePayload
from .video_engine import _get_pil_font, TARGET_W, TARGET_H, TEMP_DIR
from .config import GRAPHICS_RENDERER_VERSION

def _get_hash(scene_id: str, payload_hash_str: str) -> str:
    # Basic deterministic hash based on scene content
    return hashlib.md5(payload_hash_str.encode('utf-8')).hexdigest()[:8]

def _check_graphics_cache(out_path: str, payload_hash_str: str, scene_id: str) -> bool:
    meta_path = out_path + ".meta.json"
    if not os.path.exists(out_path) or not os.path.exists(meta_path):
        return False
    try:
        import json
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
        if meta.get("renderer_version") != GRAPHICS_RENDERER_VERSION: return False
        if meta.get("payload_hash") != _get_hash(scene_id, payload_hash_str): return False
        if meta.get("validation_status") != "valid": return False
        return True
    except Exception:
        return False

def _save_graphics_meta(out_path: str, payload_hash_str: str, scene_id: str):
    import json
    meta = {
        "renderer_version": GRAPHICS_RENDERER_VERSION,
        "payload_hash": _get_hash(scene_id, payload_hash_str),
        "validation_status": "valid"
    }
    with open(out_path + ".meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f)

def render_chart(payload: CanonicalChartPayload, duration: float, scene_id: str) -> Tuple[VideoClip, str]:
    from moviepy.editor import ImageSequenceClip, VideoFileClip
    import matplotlib.pyplot as plt
    import matplotlib.font_manager as fm
    import numpy as np
    import io
    import os
    
    out_path = os.path.join(TEMP_DIR, f"chart_{scene_id}_{hash(str(payload))}.mp4")
    if os.path.exists(out_path):
        vfc = VideoFileClip(out_path)
        vfc_dur = vfc.duration
        final_clip = vfc.fl(lambda gf, t: gf(min(t, vfc_dur - 0.01)), apply_to=['video']).set_duration(duration)
        return final_clip, out_path

    labels = payload.x_labels
    values = payload.y_values
    
    # Cinematic Dark Mode
    plt.style.use('dark_background')
    
    font_family = "sans-serif"
    
    fig, ax = plt.subplots(figsize=(16, 9), dpi=120)
    fig.patch.set_facecolor('#0D0D0D')
    ax.set_facecolor('#0D0D0D')
    
    # Grid & Spines
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.spines['bottom'].set_color('#333333')
    ax.spines['bottom'].set_linewidth(2)
    
    ax.grid(axis='y', color='#222222', linestyle='--', linewidth=1.5, alpha=0.8)
    ax.set_axisbelow(True)
    
    # Titles & Labels
    title_text = payload.chart_title
    if title_text:
        plt.title(title_text, fontsize=32, fontweight='bold', color='#fdfdfc', pad=40, fontfamily=font_family, loc='left')
        
    ax.tick_params(axis='x', colors='#a0a0a0', labelsize=16, length=0, pad=15)
    ax.tick_params(axis='y', colors='#666666', labelsize=14, length=0, pad=10)
    
    fps = 30
    anim_dur = 2.0
    frames = []
    
    max_val = max(values) if values else 1
    
    for i in range(int(fps * anim_dur) + 1):
        ax.clear()
        
        # Re-apply styles
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_visible(False)
        ax.spines['bottom'].set_color('#333333')
        ax.spines['bottom'].set_linewidth(2)
        ax.grid(axis='y', color='#222222', linestyle='--', linewidth=1.5, alpha=0.8)
        ax.set_axisbelow(True)
        if title_text:
            plt.title(title_text, fontsize=32, fontweight='bold', color='#fdfdfc', pad=40, fontfamily=font_family, loc='left')
        ax.tick_params(axis='x', colors='#a0a0a0', labelsize=16, length=0, pad=15)
        ax.tick_params(axis='y', colors='#666666', labelsize=14, length=0, pad=10)
        ax.set_ylim(0, max_val * 1.2)
        
        t = i / fps
        progress = min(1.0, t / anim_dur)
        # Smooth easing
        eased = progress * progress * (3 - 2 * progress)
        
        # Calculate how many points to draw (reveal wipe left-to-right)
        total_points = len(labels)
        visible_fraction = progress
        current_len = max(1, int(total_points * visible_fraction))
        
        x_full = np.arange(total_points)
        ax.set_xticks(x_full)
        ax.set_xticklabels(labels)
        
        if visible_fraction > 0:
            # We will render the line up to visible_fraction
            # Interpolate the exact last point for smoothness
            idx = (total_points - 1) * visible_fraction
            idx_int = int(idx)
            
            x_render = []
            y_render = []
            
            for j in range(idx_int + 1):
                x_render.append(x_full[j])
                # Grow height globally + Reveal left-to-right
                y_render.append(values[j] * eased)
                
            if idx_int < total_points - 1 and progress < 1.0:
                fraction = idx - idx_int
                interpolated_y = values[idx_int] + (values[idx_int+1] - values[idx_int]) * fraction
                x_render.append(x_full[idx_int] + fraction)
                y_render.append(interpolated_y * eased)
            
            line_color = '#39FF14' # Neon Green
            
            ax.plot(x_render, y_render, color=line_color, linewidth=5, marker='o', markersize=6, markerfacecolor='#ffffff', markeredgecolor=line_color, markeredgewidth=2)
            ax.fill_between(x_render, y_render, 0, color=line_color, alpha=0.15)
        
        plt.tight_layout(pad=3.0)
        fig.canvas.draw()
        frame = np.asarray(fig.canvas.buffer_rgba())[..., :3]
        frames.append(frame)
        
    plt.close(fig)
    
    # Hold last frame
    for _ in range(int(fps * 0.5)):
        frames.append(frames[-1])
        
    clip = ImageSequenceClip(frames, fps=fps)
    clip.write_videofile(out_path, codec='libx264', audio=False, fps=fps, preset="ultrafast", logger=None)
    
    vfc = VideoFileClip(out_path)
    vfc_dur = vfc.duration
    final_clip = vfc.fl(lambda gf, t: gf(min(t, vfc_dur - 0.01)), apply_to=['video']).set_duration(duration)
    return final_clip, out_path

def render_quote(payload: CanonicalQuotePayload, duration: float, scene_id: str) -> Tuple[VideoClip, str]:
    payload_hash_str = str(payload.model_dump())
    out_path = os.path.join(TEMP_DIR, f"quote_render_{scene_id}_{_get_hash(scene_id, payload_hash_str)}.png")
    if _check_graphics_cache(out_path, payload_hash_str, scene_id):
        return ImageClip(out_path).set_duration(duration), out_path

    img = Image.new("RGB", (TARGET_W, TARGET_H), (15, 15, 20))
    draw = ImageDraw.Draw(img)
    
    quote_text = payload.text
    author = payload.author
    
    title = payload.title
    
    font_quote = _get_pil_font(70, bold=True)
    font_author = _get_pil_font(50, bold=True)
    font_title = _get_pil_font(40)
    
    words = quote_text.split()
    lines = []
    line = ""
    for w in words:
        test_line = line + " " + w if line else w
        bbox = draw.textbbox((0,0), test_line, font=font_quote)
        if bbox[2] - bbox[0] > TARGET_W - 400:
            lines.append(line)
            line = w
        else:
            line = test_line
    if line: lines.append(line)
    
    y = 300
    for l in lines:
        bbox = draw.textbbox((0,0), l, font=font_quote)
        x = (TARGET_W - (bbox[2]-bbox[0])) / 2
        draw.text((x, y), l, font=font_quote, fill=(240,240,240))
        y += 90
        
    y += 50
    bbox = draw.textbbox((0,0), author, font=font_author)
    x = (TARGET_W - (bbox[2]-bbox[0])) / 2
    draw.text((x, y), author, font=font_author, fill=(100, 200, 255))
    
    if title:
        y += 70
        bbox = draw.textbbox((0,0), title, font=font_title)
        x = (TARGET_W - (bbox[2]-bbox[0])) / 2
        draw.text((x, y), title, font=font_title, fill=(150, 150, 150))
        
    img.save(out_path)
    _save_graphics_meta(out_path, payload_hash_str, scene_id)
    return ImageClip(out_path).set_duration(duration), out_path

def render_highlight_article(payload: CanonicalArticlePayload, duration: float, scene_id: str) -> Tuple[VideoClip, str]:
    payload_hash_str = str(payload.model_dump())
    out_path = os.path.join(TEMP_DIR, f"article_render_{scene_id}_{_get_hash(scene_id, payload_hash_str)}.mp4")
    
    def freeze_clip(clip, dur):
        return clip.fl(lambda gf, t: gf(min(t, clip.duration - 0.01)), apply_to=['video']).set_duration(dur)
        
    if _check_graphics_cache(out_path, payload_hash_str, scene_id):
        from moviepy.editor import VideoFileClip
        return freeze_clip(VideoFileClip(out_path), duration), out_path

    img = Image.new("RGB", (TARGET_W, TARGET_H), (240, 240, 245))
    draw = ImageDraw.Draw(img)
    
    source = payload.source
    headline = payload.headline
    content = payload.target_text
    
    font_src = _get_pil_font(40, bold=True)
    font_head = _get_pil_font(80, bold=True)
    font_body = _get_pil_font(50)
    
    draw.text((200, 150), source.upper(), font=font_src, fill=(100,100,100))
    
    # Wrap headline if needed
    h_words = headline.split()
    h_lines = []
    h_line = ""
    for w in h_words:
        test = h_line + " " + w if h_line else w
        if draw.textbbox((0,0), test, font=font_head)[2] > TARGET_W - 400:
            h_lines.append(h_line)
            h_line = w
        else:
            h_line = test
    if h_line: h_lines.append(h_line)
    
    hy = 220
    for hl in h_lines:
        draw.text((200, hy), hl, font=font_head, fill=(20,20,20))
        hy += 90
        
    y = hy + 60
    words = content.split()
    line = ""
    lines_data = []
    
    for w in words:
        test = line + " " + w if line else w
        if draw.textbbox((0,0), test, font=font_body)[2] > TARGET_W - 400:
            bbox = draw.textbbox((0,0), line, font=font_body)
            lines_data.append({"text": line, "y": y, "w": bbox[2]-bbox[0], "h": bbox[3]-bbox[1]})
            y += 70
            line = w
        else:
            line = test
    if line:
        bbox = draw.textbbox((0,0), line, font=font_body)
        lines_data.append({"text": line, "y": y, "w": bbox[2]-bbox[0], "h": bbox[3]-bbox[1]})

    fps = 30
    anim_duration = 1.5
    num_frames = int(fps * anim_duration)
    frames = []

    # Calculate total width for animation
    total_width = sum(l['w'] for l in lines_data)

    for i in range(num_frames + 1):
        progress = min((i / float(num_frames)), 1.0)
        
        frame_img = img.copy()
        frame_draw = ImageDraw.Draw(frame_img)
        
        current_highlight_width = total_width * progress
        
        for l in lines_data:
            if current_highlight_width > 0:
                draw_w = min(l['w'], current_highlight_width)
                frame_draw.rectangle([195, l['y']+10, 200 + draw_w + 5, l['y'] + l['h'] + 20], fill=(255, 255, 150))
                current_highlight_width -= draw_w
                
            frame_draw.text((200, l['y']), l['text'], font=font_body, fill=(10,10,10))
            
        frames.append(np.array(frame_img))

    from moviepy.editor import ImageSequenceClip, VideoFileClip
    clip = ImageSequenceClip(frames, fps=fps)
    clip.write_videofile(out_path, codec='libx264', audio=False, fps=fps, preset="ultrafast", logger=None)
    _save_graphics_meta(out_path, payload_hash_str, scene_id)
    
    final_clip = VideoFileClip(out_path)
    return freeze_clip(final_clip, duration), out_path



def render_sweeping_highlight(base_path: str, highlight_path: str, duration: float, scene_id: str) -> tuple:
    from moviepy.editor import ImageClip, CompositeVideoClip, VideoFileClip
    from PIL import Image
    import numpy as np
    import os
    
    out_path = os.path.join(TEMP_DIR, f"sweep_{scene_id}_{hash(base_path + highlight_path)}.mp4")
    if os.path.exists(out_path):
        vfc = VideoFileClip(out_path)
        vfc_dur = vfc.duration
        final_clip = vfc.fl(lambda gf, t: gf(min(t, vfc_dur - 0.01)), apply_to=['video']).set_duration(duration)
        return final_clip, out_path

    base_img = Image.open(base_path).convert("RGB")
    hl_img = Image.open(highlight_path).convert("RGB")
    w, h = base_img.size

    TARGET_W, TARGET_H = 1920, 1080
    
    scale = max(TARGET_W / w, TARGET_H / h) * 1.5
    new_w, new_h = int(w * scale), int(h * scale)
    base_img = base_img.resize((new_w, new_h), Image.LANCZOS)
    hl_img = hl_img.resize((new_w, new_h), Image.LANCZOS)
    
    crop_x = (new_w - TARGET_W) // 2
    crop_y = (new_h - TARGET_H) // 2
    base_crop = base_img.crop((crop_x, crop_y, crop_x + TARGET_W, crop_y + TARGET_H))
    hl_crop = hl_img.crop((crop_x, crop_y, crop_x + TARGET_W, crop_y + TARGET_H))
    
    base_arr = np.array(base_crop)
    hl_arr = np.array(hl_crop)
    
    fps = 30
    anim_duration = 1.5
    frames = []
    
    for i in range(int(fps * duration)):
        t = i / fps
        progress = min(1.0, t / anim_duration)
        eased = progress * progress * (3 - 2 * progress)
        
        split_x = int(TARGET_W * eased)
        frame = base_arr.copy()
        if split_x > 0:
            frame[:, :split_x] = hl_arr[:, :split_x]
        frames.append(frame)
        
    from moviepy.editor import ImageSequenceClip
    clip = ImageSequenceClip(frames, fps=fps)
    clip.write_videofile(out_path, codec='libx264', audio=False, fps=fps, preset="ultrafast", logger=None)
    
    vfc = VideoFileClip(out_path)
    vfc_dur = vfc.duration
    final_clip = vfc.fl(lambda gf, t: gf(min(t, vfc_dur - 0.01)), apply_to=['video']).set_duration(duration)
    return final_clip, out_path