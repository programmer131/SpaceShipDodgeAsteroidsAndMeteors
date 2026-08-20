# 🚀 SpaceShip Dodge: Pygame, Web & YOLO Pose Edition

A high-performance, 100% free, lightweight 2D Space Shooter in Python using **Pygame-CE** & **HTML5 Web Engine** with **Ultralytics YOLO Pose** for real-time body-gesture control via UDP & WebSockets.

---

## ⚡ Quick Start (Single Command - All 3 Apps)

To launch the **Web Server**, **Camera Pose Tracker (RTSP/Webcam)**, and **Pygame Game** simultaneously in one command:

```bash
cd python_game
./run_all.sh
```
*(Or specify a custom camera: `./run_all.sh "rtsp://192.168.1.114:554/live/ch00_1"` or `./run_all.sh 0`)*

---

## 🎮 Or Run Applications Individually

#### Option A: Pygame Desktop Game
```bash
python main.py
```

#### Option B: Web Browser Game
```bash
python server.py
```
Open **[http://localhost:8000](http://localhost:8000)** (or `http://192.168.20.103:8000` from any phone/tablet on Wi-Fi)!

---

### 3. Launch Body Tracking (YOLO Pose)

Open a **second terminal** and run:

```bash
# Using your RTSP network camera (TCP transport configured):
python pose_tracker.py "rtsp://192.168.1.114:554/live/ch00_1"

# Or with local webcam (index 0):
python pose_tracker.py 0
```

* **Body Controls**:
  * 🏃 **Lean Body Left / Right**: Steers spaceship smoothly across the bottom.
  * 🙌 **Both Hands Up**: Fires lasers (hold to keep shooting) & restarts on Game Over!
  * 💥 **Every 2nd JUMP (Body Up)**: Unleashes the Super Bomb! Jumps are counted in pairs — if more than **1 second** passes between jumps, the count resets and the next jump starts a fresh pair. Super Bombs have a **5-second cooldown**; any double jump during that window is ignored. A jump only counts if the body really lifts (elevation + shoulders level) — sideways leans used for steering and small keypoint jitter are rejected and never fire a bomb.
  * 🛑 **Press 'q' or ESC**: Closes camera window.

  *Jump detection uses the **body center (hips + shoulders)** scaled to the player's own size, so it works the same for short kids and tall adults.*

---

## 🔊 Score Announcements (TTS)

Both games speak your score at each **10,000-point** milestone ("10000", "20000", ...).

* **Pygame**: uses the **espeak-ng** command (Linux) automatically, falling back to `pyttsx3` or macOS `say` if present. On Linux just install the backend once:
  ```bash
  sudo apt install espeak-ng        # Debian/Ubuntu
  ```
  (Or `pip install pyttsx3` to use the Python engine instead.)
* **Web**: uses the browser's built-in Speech Synthesis — nothing to install.

---

## 🛠️ Project Structure

```
python_game/
├── main.py          # Pygame Space Shooter engine & UDP receiver
├── pose_tracker.py  # OpenCV + YOLOv8 pose detector (Superhero Punch & IP Cam)
├── server.py        # Python HTTP Server & WebSocket UDP Pose Bridge
├── web_game/        # 60 FPS HTML5 Canvas Browser Game & Web Audio Synth
├── requirements.txt # Python dependencies
└── README.md        # Documentation
```

---

## 🛰️ How UDP & WebSocket Networking Works

* `pose_tracker.py` broadcasts JSON telemetry to `127.0.0.1:5005`:
  ```json
  {"x": 0.45, "y": 0.8, "shoot": true}
  ```
* `main.py` (Pygame) and `server.py` (WebSocket bridge -> Browser) receive telemetry in real-time.
