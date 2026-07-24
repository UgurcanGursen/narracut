import os
import json
import time
import datetime
import functools
import threading
import psutil
import re
from contextlib import contextmanager

try:
    from rich.live import Live
    from rich.table import Table
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

SENSITIVE_KEYS = {"authorization", "cookie", "api_key", "token", "signature", "credential", "secret"}

def _redact_dict(d):
    if not isinstance(d, dict):
        return d
    redacted = {}
    for k, v in d.items():
        if any(sk in k.lower() for sk in SENSITIVE_KEYS):
            redacted[k] = "***REDACTED***"
        elif isinstance(v, dict):
            redacted[k] = _redact_dict(v)
        elif isinstance(v, list):
            redacted[k] = [_redact_dict(i) if isinstance(i, dict) else i for i in v]
        else:
            redacted[k] = v
    return redacted

def _sanitize_url(url):
    if not url or not isinstance(url, str):
        return url
    if "?" in url:
        base, query = url.split("?", 1)
        params = query.split("&")
        safe_params = []
        for p in params:
            if "=" in p:
                k, v = p.split("=", 1)
                if any(sk in k.lower() for sk in SENSITIVE_KEYS):
                    safe_params.append(f"{k}=***REDACTED***")
                else:
                    safe_params.append(p)
            else:
                safe_params.append(p)
        return f"{base}?{'&'.join(safe_params)}"
    return url

class StructuredLogger:
    def __init__(self, run_id, log_dir="output/logs"):
        self.run_id = run_id
        os.makedirs(log_dir, exist_ok=True)
        self.log_file = os.path.join(log_dir, f"{run_id}.jsonl")
        self.lock = threading.Lock()
        
    def log(self, level, phase, operation, item_id, message, elapsed_seconds=0.0, status="completed", **kwargs):
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        safe_kwargs = _redact_dict(kwargs)
        if "url" in safe_kwargs: safe_kwargs["url"] = _sanitize_url(safe_kwargs["url"])
        if "source_url" in safe_kwargs: safe_kwargs["source_url"] = _sanitize_url(safe_kwargs["source_url"])
            
        entry = {
            "timestamp": now,
            "run_id": self.run_id,
            "level": level.upper(),
            "phase": phase,
            "operation": operation,
            "item_id": item_id,
            "message": message,
            "elapsed_seconds": round(elapsed_seconds, 3),
            "status": status,
            **safe_kwargs
        }
        
        with self.lock:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")

class ResourceMonitor:
    def __init__(self, interval=1.0):
        self.interval = interval
        self.running = False
        self.thread = None
        self.samples = []
        self.process = psutil.Process(os.getpid())
        
        # Initial disk I/O to get delta later
        try:
            self.last_io = psutil.disk_io_counters()
        except:
            self.last_io = None

    def start(self):
        if self.running: return
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)

    def _run(self):
        while self.running:
            try:
                mem = psutil.virtual_memory()
                process_mem = self.process.memory_info().rss / (1024 * 1024)
                sys_cpu = psutil.cpu_percent(interval=None)
                proc_cpu = self.process.cpu_percent(interval=None)
                
                disk_read_delta = 0
                disk_write_delta = 0
                if self.last_io:
                    try:
                        io = psutil.disk_io_counters()
                        disk_read_delta = io.read_bytes - self.last_io.read_bytes
                        disk_write_delta = io.write_bytes - self.last_io.write_bytes
                        self.last_io = io
                    except:
                        pass
                
                self.samples.append({
                    "timestamp": time.time(),
                    "process_cpu_percent": proc_cpu,
                    "system_cpu_percent": sys_cpu,
                    "process_rss_mb": process_mem,
                    "available_memory_mb": mem.available / (1024 * 1024),
                    "disk_read_bytes_delta": disk_read_delta,
                    "disk_write_bytes_delta": disk_write_delta
                })
            except:
                pass
            
            time.sleep(self.interval)

class RunContext:
    _local = threading.local()

    def __init__(self, run_id=None):
        if not run_id:
            raise ValueError("RunContext MUST be initialized with an explicit run_id")
        self.run_id = run_id
        self.logger = StructuredLogger(self.run_id)
        self.metrics = {
            "phase_timings": [],
            "operation_timings": {},
            "cache_hits": 0,
            "cache_misses": 0,
            "total_start_time": time.time()
        }
        self.phases = {
            "00 INITIALIZATION": "pending",
            "01 CONFIGURATION": "pending",
            "02 TIMELINE_PARSE": "pending",
            "03 SCHEMA_VALIDATION": "pending",
            "04 MASTER_TTS": "pending",
            "05 WORD_ALIGNMENT": "pending",
            "06 CUE_MATCHING": "pending",
            "07 ABSOLUTE_SCHEDULE": "pending",
            "08 SCHEDULE_REPAIR": "pending",
            "09 ASSET_RESOLUTION": "pending",
            "10 WEB_CAPTURE": "pending",
            "11 ASSET_NORMALIZATION": "pending",
            "12 VISUAL_RENDER": "pending",
            "13 TIMELINE_COMPOSITION": "pending",
            "14 SUBTITLE_RENDER": "pending",
            "15 AUDIO_MIX": "pending",
            "16 FINAL_ENCODE": "pending",
            "17 POST_RENDER_VALIDATION": "pending",
            "18 PIXEL_VALIDATION": "pending",
            "19 EDITORIAL_VALIDATION": "pending",
            "20 REPORT_GENERATION": "pending",
            "21 PACKAGE_FINALIZATION": "pending"
        }
        self.progress_state = {
            "current_phase": "00 INITIALIZATION",
            "current_shot": "",
            "completed": 0,
            "total": 0,
            "throughput": "",
            "retry_status": "",
            "percent": 0.0,
            "start_time": time.time()
        }
        
        self.console = Console() if HAS_RICH else None
        self.live = None
        self._last_render = 0.0
        self.resource_monitor = ResourceMonitor()

    @classmethod
    def get(cls):
        if not hasattr(cls._local, "current"):
            raise ValueError("RunContext accessed before being explicitly set!")
        return cls._local.current

    @classmethod
    def set(cls, context):
        cls._local.current = context

    def log(self, level, operation, item_id, message, elapsed_seconds=0.0, status="completed", **kwargs):
        phase = self.progress_state["current_phase"]
        self.logger.log(level, phase, operation, item_id, message, elapsed_seconds, status, **kwargs)
        
    def start_console(self):
        self.resource_monitor.start()
        if HAS_RICH and self.console:
            self.live = Live(self._generate_layout(), console=self.console, refresh_per_second=2)
            self.live.start()

    def stop_console(self):
        self.resource_monitor.stop()
        if self.live:
            self.live.stop()
            self.live = None
            
    def update_progress(self, phase=None, shot=None, completed=None, total=None, throughput=None, retry_status=None, percent=None):
        if phase is not None: self.progress_state["current_phase"] = phase
        if shot is not None: self.progress_state["current_shot"] = shot
        if completed is not None: self.progress_state["completed"] = completed
        if total is not None: self.progress_state["total"] = total
        if throughput is not None: self.progress_state["throughput"] = throughput
        if retry_status is not None: self.progress_state["retry_status"] = retry_status
        if percent is not None: self.progress_state["percent"] = percent
        
        now = time.time()
        if now - self._last_render > 0.5:
            self._render_progress()
            self._last_render = now
            
    def _render_progress(self):
        if self.live:
            self.live.update(self._generate_layout())
        else:
            p = self.progress_state
            elapsed = time.time() - p["start_time"]
            print(f"[{p['current_phase']}] {p['current_shot']} - {p['completed']}/{p['total']} ({p['percent']:.1f}%) | {p['throughput']} | {elapsed:.1f}s")
            
    def _generate_layout(self):
        if not HAS_RICH: return None
        p = self.progress_state
        elapsed = time.time() - p["start_time"]
        
        mem = psutil.virtual_memory()
        cpu = psutil.cpu_percent()
        
        table = Table(show_header=False, box=None)
        table.add_row("Phase:", f"[bold cyan]{p['current_phase']}[/bold cyan]")
        table.add_row("Item:", p["current_shot"])
        table.add_row("Progress:", f"{p['completed']} / {p['total']}  ([green]{p['percent']:.1f}%[/green])")
        table.add_row("Throughput:", p["throughput"])
        if p["retry_status"]:
            table.add_row("Status:", f"[yellow]{p['retry_status']}[/yellow]")
        table.add_row("Elapsed:", f"{elapsed:.1f}s")
        table.add_row("System:", f"CPU: {cpu}% | RAM: {mem.percent}%")
        
        return Panel(table, title=f"Run: {self.run_id}", border_style="blue")


@contextmanager
def track_phase(phase_name):
    ctx = RunContext.get()
    
    if ctx and ctx.phases.get(phase_name) == "skipped":
        # Do not execute the block, just yield empty and exit. Wait, yield will execute the block!
        # Context managers must yield if we want the block to run, but we CANNOT skip the block from inside a context manager easily without throwing an exception or changing the caller.
        pass

    if ctx:
        ctx.update_progress(phase=phase_name, shot="", completed=0, total=0, percent=0.0)
        if phase_name in ctx.phases and ctx.phases[phase_name] != "skipped":
            ctx.phases[phase_name] = "in_progress"
    
    start_time = time.time()
    errors = []
    warnings = []
    status = "completed"
    
    try:
        # If it was skipped by a previous failure, we should technically not execute the block.
        # But since we use a context manager, the easiest way is to let the caller check `if ctx.phases[phase_name] == "skipped"` OR we just let it yield and the caller handles skipping. 
        yield errors, warnings
        
        if errors:
            status = "failed"
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        status = "failed"
        errors.append(str(e))
    finally:
        elapsed = time.time() - start_time
        if ctx:
            if ctx.phases.get(phase_name) == "skipped":
                status = "skipped"
                elapsed = 0.0
                
            p = ctx.progress_state
            ctx.metrics["phase_timings"].append({
                "phase": phase_name,
                "start_time": start_time,
                "end_time": time.time(),
                "elapsed_seconds": elapsed,
                "status": status,
                "items_total": p["total"],
                "items_completed": p["completed"],
                "warnings": warnings,
                "errors": errors
            })
            if phase_name in ctx.phases:
                ctx.phases[phase_name] = status
                
            # If failed, mark the rest as skipped, except reporting phases
            if status == "failed":
                for k in ctx.phases:
                    if ctx.phases[k] == "pending" and k not in ("17 POST_RENDER_VALIDATION", "18 PIXEL_VALIDATION", "19 EDITORIAL_VALIDATION", "20 REPORT_GENERATION", "21 PACKAGE_FINALIZATION"):
                        ctx.phases[k] = "skipped"
                        
            if status != "skipped":
                ctx.log("INFO", "phase_complete", "", f"Phase {phase_name} {status}", elapsed_seconds=elapsed, status=status)

def measure_time(operation):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            ctx = RunContext.get()
            try:
                result = func(*args, **kwargs)
                status = "completed"
                return result
            except Exception as e:
                status = "failed"
                raise
            finally:
                elapsed = time.time() - start_time
                if ctx:
                    if operation not in ctx.metrics["operation_timings"]:
                        ctx.metrics["operation_timings"][operation] = []
                    ctx.metrics["operation_timings"][operation].append(elapsed)
                    # For specific operations requested by user, log explicitly
                    ctx.log("INFO", operation, "", f"Completed in {elapsed:.2f}s", elapsed_seconds=elapsed, status=status)
        return wrapper
    return decorator

def parse_ffmpeg_progress(line, state, expected_duration_sec):
    if "=" not in line: return
    k, v = line.split("=", 1)
    k = k.strip()
    v = v.strip()
    
    if k == "frame":
        state["frame"] = int(v) if v.isdigit() else state.get("frame", 0)
    elif k == "fps":
        try:
            fps_val = float(v)
            state["fps"] = fps_val
            if "fps_samples" not in state: state["fps_samples"] = []
            state["fps_samples"].append((time.time(), fps_val))
        except: pass
    elif k == "speed":
        state["speed"] = v
        try:
            # speed could be "1.23x"
            speed_val = float(v.replace("x", "").strip())
            if "speed_samples" not in state: state["speed_samples"] = []
            state["speed_samples"].append((time.time(), speed_val))
        except: pass
    elif k == "bitrate":
        state["bitrate"] = v
    elif k == "total_size":
        try: state["total_size"] = int(v)
        except: pass
    elif k == "dup_frames":
        try: state["dup_frames"] = int(v)
        except: pass
    elif k == "drop_frames":
        try: state["drop_frames"] = int(v)
        except: pass
    elif k == "out_time_us":
        try: state["out_time_sec"] = float(v) / 1000000.0
        except: pass
    elif k == "out_time_ms":
        try: state["out_time_sec"] = float(v) / 1000000.0
        except: pass
    elif k == "out_time":
        if ":" in v:
            parts = v.split(":")
            if len(parts) == 3:
                try:
                    h, m, s = int(parts[0]), int(parts[1]), float(parts[2])
                    state["out_time_sec"] = h * 3600 + m * 60 + s
                except: pass
                
    if "out_time_sec" in state and expected_duration_sec > 0:
        state["percent"] = (state["out_time_sec"] / expected_duration_sec) * 100.0
