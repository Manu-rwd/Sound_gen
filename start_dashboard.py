"""Launcher script for the biosignal dashboard.

Starts both the FastAPI backend and the Vite frontend in separate processes.
"""
import subprocess
import sys
import os
import signal
import time
from pathlib import Path

def main():
    root_dir = Path(__file__).parent
    backend_dir = root_dir / "biosignal_dashboard" / "backend"
    frontend_dir = root_dir / "biosignal_dashboard" / "frontend"
    
    # Determine python executable in venv
    venv_python = backend_dir / ".venv" / "Scripts" / "python.exe"
    if not venv_python.exists():
        print(f"Error: Virtual environment not found at {venv_python}")
        print("Please run implementation setup first.")
        sys.exit(1)

    print(f"Starting Dashboard from {root_dir}...")
    
    processes = []
    
    # We need to set PYTHONPATH so it can find dashboard_backend package
    env = os.environ.copy()
    env["PYTHONPATH"] = str(backend_dir / "src")

    # Load .env variables manually to ensure backend sees them
    env_file = backend_dir / ".env"
    if env_file.exists():
        print(f"Loading environment from {env_file}")
        with open(env_file, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, value = line.split("=", 1)
                    env[key.strip()] = value.strip()
                    print(f"  Set {key.strip()}={value.strip()}")
    else:
        print("Warning: No .env file found in backend directory!")

    try:
        # 1. Start Backend
        print("Starting Backend (Uvicorn)...")
        backend_cmd = [
            str(venv_python), "-m", "uvicorn", 
            "dashboard_backend.main:app", 
            "--host", "127.0.0.1", 
            "--port", "8000", 
            "--reload"
        ]
        
        backend_proc = subprocess.Popen(
            backend_cmd, 
            cwd=backend_dir,
            env=env,
            shell=True 
        )
        processes.append(backend_proc)
        
        # Wait a moment for backend to initialize
        time.sleep(2)
        
        # 2. Start Frontend
        print("Starting Frontend (Vite)...")
        npm_cmd = ["npm", "run", "dev"]
        frontend_proc = subprocess.Popen(
            npm_cmd, 
            cwd=frontend_dir, 
            shell=True
        )
        processes.append(frontend_proc)
        
        print("\n" + "="*50)
        print("DASHBOARD RUNNING")
        print("Backend: http://127.0.0.1:8000")
        print("Frontend: http://127.0.0.1:5173")
        print("Press Ctrl+C to stop all services")
        print("="*50 + "\n")
        
        # Keep main process alive
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nStopping services...")
    finally:
        for p in processes:
            # On Windows, we might need a stronger kill if shell=True spawned children
            # But simple poll/terminate is a start
            if p.poll() is None:
                p.terminate()
        print("Done.")

if __name__ == "__main__":
    main()
