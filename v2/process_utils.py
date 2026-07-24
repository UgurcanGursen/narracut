import subprocess
import psutil
import time
import os

def get_current_pid() -> int:
    return os.getpid()

def is_process_alive(pid: int) -> bool:
    """Checks if a process with the given PID is currently running."""
    try:
        proc = psutil.Process(pid)
        return proc.is_running() and proc.status() != psutil.STATUS_ZOMBIE
    except psutil.NoSuchProcess:
        return False

def kill_process_tree(pid: int):
    """
    Kills the process and all its children gracefully.
    """
    try:
        parent = psutil.Process(pid)
    except psutil.NoSuchProcess:
        return
        
    children = parent.children(recursive=True)
    
    for child in children:
        try:
            child.kill()
        except psutil.NoSuchProcess:
            pass
            
    try:
        parent.kill()
    except psutil.NoSuchProcess:
        pass
        
    # Wait for them to die
    psutil.wait_procs(children + [parent], timeout=3)

def run_process_with_timeout(cmd: list, timeout: float = 45.0) -> dict:
    """
    Runs a command and terminates the whole process tree if it times out.
    Returns {"success": bool, "reason": str}
    """
    # Use CREATE_NEW_PROCESS_GROUP on Windows to better isolate signals if needed
    # but psutil handles tree killing well enough.
    
    start_time = time.time()
    proc = None
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        while True:
            retcode = proc.poll()
            if retcode is not None:
                if retcode == 0:
                    return {"success": True, "reason": "completed"}
                else:
                    return {"success": False, "reason": f"exit_code_{retcode}"}
                    
            if time.time() - start_time > timeout:
                kill_process_tree(proc.pid)
                return {"success": False, "reason": "timeout"}
                
            time.sleep(0.5)
            
    except Exception as e:
        if proc:
            kill_process_tree(proc.pid)
        return {"success": False, "reason": f"exception: {str(e)}"}
