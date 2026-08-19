# 🚀 SpaceShip Dodge: Pygame + YOLO Pose Edition

A high-performance, 100% free, lightweight 2D Space Shooter in Python using **Pygame-CE** for the game engine and **Ultralytics YOLO Pose** with OpenCV for real-time body-gesture control via UDP.

---

## ⚡ Quick Start

### 1. Install Dependencies
Run the following in your Linux terminal:

```bash
pip install -r requirements.txt
```
*(Or manually: `pip install pygame-ce opencv-python ultralytics numpy`)*

---

### 2. Launch the Game

Open a terminal and run:

```bash
python main.py
```
> **Note:** The game starts immediately! If no webcam or pose tracker is active, you can play using **Arrow Keys / WASD + Spacebar**.

---

### 3. Launch Body Tracking (YOLO Pose)

Open a **second terminal** and run:

```bash
python pose_tracker.py
```

* On first run, it will automatically download the tiny `yolov8n-pose.pt` model (~6MB).
* Your camera window will open with a real-time skeleton overlay and steering gauge.
* **Body Controls**:
  * 🏃 **Lean Body Left / Right**: Moves spaceship across the screen.
  * 🙋 **Raise Hands above Shoulders**: Shoots lasers!
  * 🛑 **Press 'q' or ESC in camera window**: Closes tracking.

---

## 🛠️ Project Structure

```
python_game/
├── main.py          # Pygame Space Shooter engine & UDP receiver
├── pose_tracker.py  # OpenCV + YOLOv8 pose detector & UDP sender
├── requirements.txt # Python dependencies
└── README.md        # Documentation
```

---

## 🛰️ How UDP Networking Works

* `pose_tracker.py` broadcasts JSON telemetry to `127.0.0.1:5005` at camera framerate:
  ```json
  {"x": 0.45, "y": 0.8, "shoot": true}
  ```
* `main.py` runs a background non-blocking UDP receiver thread at 60 FPS and smoothly lerps the spaceship towards `(x, y)` target coordinates.
