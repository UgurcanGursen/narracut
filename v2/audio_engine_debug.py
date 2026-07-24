import os
import asyncio
import numpy as np
import pyloudnorm as pyln
import soundfile as sf
import requests
import shutil
from faster_whisper import WhisperModel
from moviepy.editor import AudioFileClip, concatenate_audioclips
from moviepy.audio.AudioClip import AudioClip
from moviepy.audio.fx.volumex import volumex
from moviepy.audio.fx.audio_loop import audio_loop

try:
    import edge_tts
except ImportError:
    edge_tts = None

import difflib
from .number_normalizer import canonicalize_numbers

def _is_numeric_match(c_val: str, w_val: str) -> bool:
    if c_val == w_val:
        return True
    try:
        cf = float(c_val)
        wf = float(w_val)
        if int(cf) == int(wf) and len(c_val) <= len(w_val):
            return True
    except ValueError:
        pass
    return False

def get_audio_duration(path: str) -> float:
    if not os.path.exists(path):
        return 0.0
    try:
        with AudioFileClip(path) as clip:
            return clip.duration
    except Exception:
        return 0.0

from .config import USE_ELEVENLABS, ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID, ELEVENLABS_MODEL, EDGE_TTS_RATE, TTS_TARGET_WPM, TTS_WPM_TOLERANCE

def measure_wpm(audio_path: str, word_count: int) -> dict:
    if not os.path.exists(audio_path):
        return {"gross_wpm": 0, "active_wpm": 0, "status": "invalid"}
    gross_dur = get_audio_duration(audio_path)
    if gross_dur <= 0: 
        return {"gross_wpm": 0, "active_wpm": 0, "status": "invalid"}
    
    gross_wpm = (word_count / gross_dur) * 60
    
    try:
        data, rate = sf.read(audio_path)
        if len(data.shape) > 1: data = np.mean(data, axis=1) # to mono
        frame_len = int(rate * 0.02) # 20ms frames
        active_frames = 0
        threshold = 0.005 
        for i in range(0, len(data), frame_len):
            frame = data[i:i+frame_len]
            if np.max(np.abs(frame)) > threshold:
                active_frames += 1
        active_dur = active_frames * 0.02
        if active_dur < 0.1: active_dur = gross_dur
    except Exception:
        active_dur = gross_dur
        
    active_wpm = (word_count / active_dur) * 60
    status = "valid" if TTS_TARGET_WPM - TTS_WPM_TOLERANCE <= active_wpm <= TTS_TARGET_WPM + TTS_WPM_TOLERANCE else "out_of_range"
    
    return {
        "word_count": word_count,
        "gross_duration": round(gross_dur, 2),
        "active_duration": round(active_dur, 2),
        "gross_wpm": round(gross_wpm, 1),
        "active_wpm": round(active_wpm, 1),
        "status": status
    }

def generate_elevenlabs_tts(text: str, output_path: str) -> bool:
    if not ELEVENLABS_API_KEY or not ELEVENLABS_VOICE_ID:
        return False
        
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": ELEVENLABS_API_KEY
    }
    data = {
        "text": text,
        "model_id": ELEVENLABS_MODEL,
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75
        }
    }
    
    try:
        response = requests.post(url, json=data, headers=headers, timeout=30)
        if response.status_code == 200:
            with open(output_path, "wb") as f:
                f.write(response.content)
            return True
    except Exception:
        pass
    return False

def resolve_audio_for_block(block, output_path: str) -> bool:
    if getattr(block, "audio_file", None) and os.path.exists(block.audio_file):
        try:
            shutil.copy(block.audio_file, output_path)
            return True
        except Exception:
            pass
            
    if USE_ELEVENLABS and ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID:
        success = generate_elevenlabs_tts(block.narration, output_path)
        if success:
            return True
            
    if edge_tts:
        try:
            generate_tts_edge_sync(block.narration, output_path)
            return True
        except Exception:
            pass
            
    return False

def generate_tts_edge_sync(text: str, output_path: str, voice: str = "en-US-ChristopherNeural") -> None:
    if not edge_tts:
        raise RuntimeError("edge_tts not installed.")
    
    async def _gen():
        communicate = edge_tts.Communicate(text, voice, rate=EDGE_TTS_RATE)
        await communicate.save(output_path)
        
    asyncio.run(_gen())

def transcribe_audio_aligned(audio_path: str) -> list:
    if not os.path.exists(audio_path):
        return []
        
    model = WhisperModel("base", device="cpu", compute_type="int8")
    segments, info = model.transcribe(audio_path, word_timestamps=True)
    
    words = []
    for segment in segments:
        for word in segment.words:
            words.append({
                "start": word.start,
                "end": word.end,
                "word": word.word.strip()
            })
    return words

def align_narration_once(audio_path: str, original_text: str = "") -> list:
    words = transcribe_audio_aligned(audio_path)
    if not words or not original_text:
        return words
        
    orig_words = original_text.split()
    if len(orig_words) == len(words):
        for i, item in enumerate(words):
            item["word"] = orig_words[i]
    else:
        for i, item in enumerate(words):
            w_w = item["word"].strip(".,!?;:\\\"'()").lower()
            for ow in orig_words:
                ow_clean = ow.strip(".,!?;:\\\"'()").lower()
                if w_w == ow_clean and ow and ow[0].isupper():
                    item["word"] = ow
                    break
    return words

def find_cue_time(words: list, cue_text: str, return_end: bool = False, min_start_time: float = 0.0) -> dict:
    from .number_normalizer import canonicalize_numbers
    import difflib
    
    empty_details = {
        "token_similarity": 0.0, "order_score": 0.0, "contiguous_score": 0.0,
        "position_score": 0.0, "semantic_number_score": 0.0, "negation_score": 0.0,
        "gap_penalty": 0.0, "final_confidence": 0.0, "ambiguity_margin": 0.0
    }
    
    if not cue_text or not words:
        return {"time": -1.0, "score": 0.0, "matched_text": "", "normalized_matched_text": "", "ambiguity_margin": 0.0, "original_cue": cue_text, "normalized_cue": "", "matching_method": "ordered_local_alignment", "details": empty_details}
        
    cue_norm = canonicalize_numbers(cue_text)
    cue_words = [t["word"] for t in cue_norm.tokens if t["word"].strip()]
    
    if not cue_words:
        return {"time": -1.0, "score": 0.0, "matched_text": "", "normalized_matched_text": "", "ambiguity_margin": 0.0, "original_cue": cue_text, "normalized_cue": cue_norm.normalized_text, "matching_method": "ordered_local_alignment", "details": empty_details}
        
    # Normalize whisper words and flat-map them
    transcript_norm = canonicalize_numbers(words)
    norm_words = [t for t in transcript_norm.tokens if t["word"].strip()]
            
    # Filter candidates by min_start_time
    valid_words = [w for w in norm_words if w["start"] >= min_start_time]
    
    candidates = []
    window_size = len(cue_words) + 10
    
    for i in range(len(valid_words)):
        window = valid_words[i:i+window_size]
        window_texts = [w["word"] for w in window]
        
        # Find candidate windows using SequenceMatcher for speed
        sm = difflib.SequenceMatcher(None, cue_words, window_texts)
        if sm.ratio() < 0.2: # Very low ratio, not a candidate
            continue
            
        # Perform Local DP Alignment (Smith-Waterman inspired)
        # Match = 1.0, Mismatch = -0.5, Gap = -0.3
        m, n = len(cue_words), len(window_texts)
        dp = [[0.0 for _ in range(n + 1)] for _ in range(m + 1)]
        
        max_score = 0.0
        max_i, max_j = 0, 0
        
        for ci in range(1, m + 1):
            for wj in range(1, n + 1):
                c_word = cue_words[ci-1]
                w_word = window_texts[wj-1]
                
                is_match = False
                c_clean = c_word.lower().strip(".,!?;:\\\"'()")
                w_clean = w_word.lower().strip(".,!?;:\\\"'()")
                
                if c_clean == w_clean:
                    is_match = True
                elif c_word.startswith("<NUM:") and w_word.startswith("<NUM:"):
                    # Extract the numeric part (last segment after colon, up to >)
                    c_val = c_word.split(":")[-1].replace(">", "")
                    w_val = w_word.split(":")[-1].replace(">", "")
                    if _is_numeric_match(c_val, w_val):
                        is_match = True
                        
                match_score = 1.0 if is_match else -0.5
                
                diag = dp[ci-1][wj-1] + match_score
                up = dp[ci-1][wj] - 0.3
                left = dp[ci][wj-1] - 0.3
                
                val = max(0.0, diag, up, left)
                dp[ci][wj] = val
                
                if val > max_score:
                    max_score = val
                    max_i = ci
                    max_j = wj
                    
        if max_score == 0.0:
            continue
            
        # Backtrack to find the matching region in the window
        curr_i, curr_j = max_i, max_j
        match_path = []
        while curr_i > 0 and curr_j > 0 and dp[curr_i][curr_j] > 0.0:
            c_word = cue_words[curr_i-1]
            w_word = window_texts[curr_j-1]
            
            is_match = False
            c_clean = c_word.lower().strip(".,!?;:\\\"'()")
            w_clean = w_word.lower().strip(".,!?;:\\\"'()")
            
            if c_clean == w_clean:
                is_match = True
            elif c_word.startswith("<NUM:") and w_word.startswith("<NUM:"):
                c_val = c_word.split(":")[-1].replace(">", "")
                w_val = w_word.split(":")[-1].replace(">", "")
                if _is_numeric_match(c_val, w_val):
                    is_match = True
                    
            if abs(dp[curr_i][curr_j] - (dp[curr_i-1][curr_j-1] + (1.0 if is_match else -0.5))) < 1e-6:
                if is_match:
                    match_path.append((curr_i-1, curr_j-1))
                curr_i -= 1
                curr_j -= 1
            elif abs(dp[curr_i][curr_j] - (dp[curr_i-1][curr_j] - 0.3)) < 1e-6:
                curr_i -= 1
            else:
                curr_j -= 1
                
        if not match_path:
            continue
            
        match_path.reverse()
        start_idx = match_path[0][1]
        end_idx = match_path[-1][1]
        
        matched_tokens = len(match_path)
        token_similarity = matched_tokens / len(cue_words)
        
        order_score = 1.0 # DP backtracking naturally guarantees order
        
        # Calculate contiguous score and gaps based on the window indices in match_path
        num_blocks = 1
        gaps = 0
        for k in range(1, len(match_path)):
            gap_size = match_path[k][1] - match_path[k-1][1] - 1
            if gap_size > 0:
                num_blocks += 1
                gaps += gap_size
                
        contiguous_score = 1.0 if num_blocks == 1 else max(0.0, 1.0 - ((num_blocks - 1) * 0.15))
        gap_penalty = gaps * 0.06
        position_score = max(0.0, 1.0 - (i * 0.005))
        
        start_orig_idx = window[start_idx].get("orig_idx", 0)
        
        end_token = window[end_idx]
        if end_token.get("is_canonical"):
            end_orig_idx = end_token["entity"].get("original_token_end_index", len(words) - 1)
        else:
            end_orig_idx = end_token.get("orig_idx", len(words) - 1)
        
        # reconstruct matched_orig using the original words array
        matched_orig = " ".join([w.get("word", "") for w in words[start_orig_idx:end_orig_idx+1]])
        matched_norm = " ".join([w["word"] for w in window[start_idx:end_idx+1]])
        
        # Semantic Analysis: Numbers
        cue_nums = {e["canonical_token"] for e in cue_norm.semantic_entities}
        
        matched_nums = set()
        for e in transcript_norm.semantic_entities:
            if start_orig_idx <= e["original_token_start_index"] and e["original_token_end_index"] <= end_orig_idx:
                matched_nums.add(e["canonical_token"])
                
        semantic_number_score = 1.0
        if cue_nums:
            c_vals = {c.split(":")[-1].replace(">", "") for c in cue_nums if c.startswith("<NUM:")}
            w_vals = {w.split(":")[-1].replace(">", "") for w in matched_nums if w.startswith("<NUM:")}
            
            # Check if all c_vals have a match in w_vals
            all_matched = True
            for c in c_vals:
                if not any(_is_numeric_match(c, w) for w in w_vals):
                    all_matched = False
                    break
            
            if not all_matched or len(c_vals) != len(w_vals):
                # We do not fail completely if it's a prefix, but if they are entirely mismatched, we zero it
                if not all_matched:
                    semantic_number_score = 0.0
                
        # Semantic Analysis: Negation
        negations = {"not", "no", "never", "none", "didn't", "don't", "doesn't", "isn't", "aren't"}
        cue_negs = set(w for w in cue_words if w in negations)
        matched_negs = set(w for w in window_texts[start_idx:end_idx+1] if w in negations)
        negation_score = 1.0
        if cue_negs or matched_negs:
            if cue_negs != matched_negs:
                negation_score = 0.0
                
        base_alignment_score = (token_similarity * 0.6) + (contiguous_score * 0.2) + (position_score * 0.2)
        final_confidence = (base_alignment_score * semantic_number_score * negation_score) - gap_penalty
            
        final_confidence = max(0.0, min(1.0, final_confidence))
        
        matched_time = window[end_idx]["end"] if return_end else window[start_idx]["start"]
        
        candidates.append({
            "time": matched_time,
            "score": final_confidence,
            "matched_text": matched_orig,
            "normalized_matched_text": matched_norm,
            "details": {
                "token_similarity": round(token_similarity, 3),
                "order_score": round(order_score, 3),
                "contiguous_score": round(contiguous_score, 3),
                "position_score": round(position_score, 3),
                "semantic_number_score": round(semantic_number_score, 3),
                "negation_score": round(negation_score, 3),
                "gap_penalty": round(gap_penalty, 3),
                "final_confidence": round(final_confidence, 3)
            }
        })
        
    # Deduplicate candidates based on matched time and text
    unique_candidates = []
    seen = set()
    for c in candidates:
        key = (c["time"], c["matched_text"])
        if key not in seen:
            seen.add(key)
            unique_candidates.append(c)
            
    unique_candidates.sort(key=lambda x: x["score"], reverse=True)
      for m in unique_candidates[:5]: print("UNIQ:", m["score"], m["matched_text"])
      for m in unique_candidates[:5]: print("UNIQ:", m["score"], m["matched_text"])
    
    if not unique_candidates:
        return {"time": -1.0, "score": 0.0, "matched_text": "", "normalized_matched_text": "", "ambiguity_margin": 0.0, "original_cue": cue_text, "normalized_cue": cue_norm.normalized_text, "matching_method": "ordered_local_alignment", "details": empty_details}
        
    best = unique_candidates[0]
    
    if len(unique_candidates) > 1:
        ambiguity_margin = best["score"] - unique_candidates[1]["score"]
    else:
        ambiguity_margin = 1.0
        
    if ambiguity_margin == 0.0 and best["score"] > 0.0:
        # Exact duplicate matches -> unsafe!
        best["score"] = 0.0
        best["details"]["final_confidence"] = 0.0
        
    best["ambiguity_margin"] = round(ambiguity_margin, 3)
    best["original_cue"] = cue_text
    best["normalized_cue"] = cue_norm.normalized_text
    best["matching_method"] = "ordered_local_alignment"
    best["details"]["ambiguity_margin"] = round(ambiguity_margin, 3)
    
    return best

def normalize_lufs(input_path: str, output_path: str, target_lufs: float = -15.0, target_tp: float = -1.0) -> None:
    if not os.path.exists(input_path):
        return
        
    data, rate = sf.read(input_path)
    meter = pyln.Meter(rate)
    
    peak_normalized_audio = pyln.normalize.peak(data, target_tp)
    loudness = meter.integrated_loudness(peak_normalized_audio)
    
    try:
        loudness_normalized_audio = pyln.normalize.loudness(peak_normalized_audio, loudness, target_lufs)
    except Exception:
        loudness_normalized_audio = peak_normalized_audio
        
    sf.write(output_path, loudness_normalized_audio, rate)

def mix_master_audio(narration_paths: list, pauses_before: list, pauses_after: list, output_path: str) -> dict:
    def make_silence(d):
        import numpy as np
        return AudioClip(lambda t: np.zeros((len(t), 2)) if hasattr(t, '__len__') else [0,0], duration=d, fps=44100)
        
    clips = []
    timings = []
    current_time = 0.0
    
    for i, path in enumerate(narration_paths):
        pb = pauses_before[i]
        pa = pauses_after[i]
        
        if pb > 0:
            clips.append(make_silence(pb))
        current_time += pb
        
        start_time = current_time
        
        n_dur = 0.0
        if os.path.exists(path):
            n_clip = AudioFileClip(path)
            clips.append(n_clip)
            n_dur = n_clip.duration
            current_time += n_dur
            
        end_time = current_time
        
        if pa > 0:
            clips.append(make_silence(pa))
        current_time += pa
        
        timings.append({
            "block_idx": i,
            "start": start_time - pb,
            "narration_start": start_time,
            "narration_end": end_time,
            "end": current_time
        })
        
    if clips:
        master = concatenate_audioclips(clips)
        master.write_audiofile(output_path, fps=44100, logger=None)
        master.close()
    else:
        # Fallback if no audio
        master = make_silence(1.0)
        master.write_audiofile(output_path, fps=44100, logger=None)
        
    return timings

def apply_bgm_ducking(bgm_path: str, duck_cues: list, output_path: str, master_duration: float) -> None:
    if not os.path.exists(bgm_path):
        return
        
    bgm = AudioFileClip(bgm_path)
    if bgm.duration < master_duration:
        bgm = audio_loop(bgm, duration=master_duration)
    else:
        bgm = bgm.subclip(0, master_duration)
        
    bgm = volumex(bgm, 0.2)
    
    def duck_filter(get_frame, t):
        vol = 1.0
        for cue in duck_cues:
            start_t = cue["time"]
            end_t = start_t + cue["duration"]
            
            if start_t <= t <= end_t:
                vol = 0.3
            elif start_t - 0.2 <= t < start_t:
                progress = (t - (start_t - 0.2)) / 0.2
                vol = 1.0 - (0.7 * progress)
            elif end_t < t <= end_t + 0.8:
                progress = (t - end_t) / 0.8
                vol = 0.3 + (0.7 * progress)
                
        frame = get_frame(t)
        return frame * vol
        
    bgm = bgm.fl(duck_filter)
    bgm.write_audiofile(output_path, fps=44100, logger=None)
    bgm.close()

def generate_sfx_track(sfx_cues: list, master_duration: float):
    import random
    from moviepy.editor import CompositeAudioClip
    
    if not sfx_cues: return None
    clips = []
    
    for cue in sfx_cues:
        cat = cue.get("category", "whooshes")
        t = cue.get("time", 0.0)
        
        sfx_dir = os.path.join("assets", "sfx", cat)
        if os.path.exists(sfx_dir):
            files = [os.path.join(sfx_dir, f) for f in os.listdir(sfx_dir) if f.endswith(".wav") or f.endswith(".mp3")]
            if files:
                fpath = random.choice(files)
                try:
                    c = AudioFileClip(fpath).set_start(t)
                    c = volumex(c, 0.4)
                    clips.append(c)
                except Exception:
                    pass
                    
    if clips:
        import numpy as np
        silent_base = AudioClip(lambda t: np.zeros((len(t), 2)) if hasattr(t, '__len__') else [0,0], duration=master_duration, fps=44100)
        return CompositeAudioClip([silent_base] + clips).set_duration(master_duration)
    return None

def generate_pacing_report(words: list, audio_duration: float) -> dict:
    if not words:
        return {"status": "invalid", "reasons": ["No words found"]}
        
    word_count = len(words)
    total_silence = 0.0
    longest_pause = 0.0
    pauses = []
    pause_count_over_800ms = 0
    
    for i in range(1, len(words)):
        pause = words[i]["start"] - words[i-1]["end"]
        if pause > 0:
            pauses.append(pause)
            total_silence += pause
            if pause > longest_pause:
                longest_pause = pause
            if pause > 0.8:
                pause_count_over_800ms += 1
                
    speech_active = audio_duration - total_silence
    if speech_active <= 0: speech_active = 0.1
    
    gross_wpm = (word_count / audio_duration) * 60
    active_wpm = (word_count / speech_active) * 60
    mean_pause = np.mean(pauses) if pauses else 0.0
    
    status = "valid"
    reasons = []
    
    if not (120 <= gross_wpm <= 140):
        status = "invalid"
        reasons.append(f"Gross WPM out of bounds: {gross_wpm:.1f} (Target: 120-140)")
        
    if not (135 <= active_wpm <= 150):
        status = "invalid"
        reasons.append(f"Active WPM out of bounds: {active_wpm:.1f} (Target: 135-150)")
        
    if pauses and not (0.22 <= mean_pause <= 0.45):
        status = "invalid"
        reasons.append(f"Mean sentence pause out of bounds: {mean_pause:.3f}s (Target: 220-450ms)")
        
    return {
        "status": status,
        "reasons": reasons,
        "word_count": word_count,
        "audio_duration": audio_duration,
        "speech_active_duration": round(speech_active, 2),
        "gross_wpm": round(gross_wpm, 1),
        "active_wpm": round(active_wpm, 1),
        "total_silence_duration": round(total_silence, 2),
        "mean_sentence_pause": round(mean_pause, 3),
        "longest_pause": round(longest_pause, 3),
        "pause_count_over_800ms": pause_count_over_800ms
    }
