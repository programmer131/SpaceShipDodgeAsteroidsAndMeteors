# 🚀 SpaceShip Dodge: Pygame, Web & YOLO Pose Edition

A high-performance, 100% free, lightweight 2D Space Shooter in Python using **Pygame-CE** & **HTML5 Web Engine** with **Ultralytics YOLO Pose** for real-time body-gesture control via UDP & WebSockets.

---

## ⚡ Quick Start

### 1. Install Dependencies
Run the following in your Linux terminal:

```bash
pip install -r requirements.txt
```
*(Dependencies: `pygame-ce opencv-python ultralytics numpy`)*

---

### 2. Launch the Game (Desktop Pygame OR Web Browser)

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
python pose_tracker.py
```
*(To use a network/phone IP camera URL, run: `python pose_tracker.py http://192.168.20.103:8080/video`)*

* **Body Controls**:
  * 🏃 **Lean Body Left / Right**: Moves spaceship smoothly across the screen.
  * 🥊 **Superhero Punch (Thrust Arm Forward)**: Shoots lasers!
  * 👏 **Power Clap (Hands Together)**: Shoots lasers!
  * 🛑 **Press 'q' or ESC**: Closes camera window.

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
