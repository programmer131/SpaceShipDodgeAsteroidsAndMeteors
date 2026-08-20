#!/usr/bin/env python3
"""
SpaceShip Dodge: Unified Multi-Application Launcher
Starts all 3 components concurrently:
1. Web Server & WebSocket Pose Bridge (server.py) -> http://localhost:8000
2. YOLOv8 Pose Tracker & Gesture Recognizer (pose_tracker.py)
3. Pygame 2D Arcade Space Shooter Game (main.py)

Press ESC / close the game window or hit Ctrl+C to cleanly terminate all processes.
"""

import sys
import os
import time
import signal
import subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
VENV_PYTHON = os.path.join(SCRIPT_DIR, ".venv", "bin", "python")
PYTHON_EXEC = VENV_PYTHON if os.path.exists(VENV_PYTHON) else sys.executable

DEFAULT_CAMERA = "rtsp://192.168.1.114:554/live/ch00_1"

def print_banner(cam_source):
    print("=" * 65)
    print("  🚀 SPACESHIP DODGE - UNIFIED SYSTEM LAUNCHER")
    print("=" * 65)
    print(f"  [1] Web Game & Bridge:  http://localhost:8000 (ws://localhost:8080)")
    print(f"  [2] YOLO Pose Tracker:  Camera feed -> {cam_source}")
    print(f"                          (Mirror Flip: ON | Press 'f' to toggle)")
    print(f"  [3] Desktop Arcade:     Pygame Game (60 FPS)")
    print("-" * 65)
    print("  🕹️  Gestures: Lean to steer | 🦘 JUMP (Body/Head Up) to shoot")
    print("                Raise hands to Super Bomb & Restart on Game Over")
    print("  🛑 Exit:     Close game window, press ESC, or Ctrl+C in terminal")
    print("=" * 65 + "\n")

def main():
    cam_source = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_CAMERA
    print_banner(cam_source)

    processes = []

    def cleanup(signum=None, frame=None):
        print("\n[Launcher] Shutting down all applications...")
        for name, proc in reversed(processes):
            if proc.poll() is None:
                print(f"[Launcher] Stopping {name} (PID {proc.pid})...")
                proc.terminate()
        
        # Wait up to 2 seconds for graceful termination
        start_time = time.time()
        for name, proc in processes:
            while proc.poll() is None and (time.time() - start_time) < 2.0:
                time.sleep(0.1)
            if proc.poll() is None:
                proc.kill()
        print("[Launcher] All processes terminated cleanly. Goodbye!\n")
        sys.exit(0)

    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    try:
        # 1. Start Web Server & WebSocket Bridge
        print("[1/3] Starting Web Server & WebSocket Pose Bridge (server.py)...")
        server_proc = subprocess.Popen(
            [PYTHON_EXEC, os.path.join(SCRIPT_DIR, "server.py")],
            cwd=SCRIPT_DIR
        )
        processes.append(("Web Server", server_proc))
        time.sleep(0.6)

        # 2. Start YOLO Pose Tracker
        print(f"[2/3] Starting YOLO Pose Tracker with camera '{cam_source}' (pose_tracker.py)...")
        tracker_proc = subprocess.Popen(
            [PYTHON_EXEC, os.path.join(SCRIPT_DIR, "pose_tracker.py"), cam_source],
            cwd=SCRIPT_DIR
        )
        processes.append(("YOLO Pose Tracker", tracker_proc))
        time.sleep(0.8)

        # 3. Start Pygame Desktop Game (Foreground)
        print("[3/3] Launching Pygame Desktop Game (main.py)...")
        game_proc = subprocess.Popen(
            [PYTHON_EXEC, os.path.join(SCRIPT_DIR, "main.py")],
            cwd=SCRIPT_DIR
        )
        processes.append(("Pygame Game", game_proc))

        # Wait for the Pygame Game or any child to exit
        while True:
            # If the desktop game window is closed, trigger shutdown of all apps
            if game_proc.poll() is not None:
                print("\n[Launcher] Pygame Game window closed.")
                break
            
            # If the pose tracker was closed with 'q'/ESC, keep the game running or notify
            if tracker_proc.poll() is not None:
                print("\n[Launcher] Camera Pose Tracker window closed.")
                break

            time.sleep(0.3)

    except Exception as e:
        print(f"[Launcher Error] {e}")
    finally:
        cleanup()

if __name__ == "__main__":
    main()
