#!/usr/bin/env python3
"""
YOLOv8 Pose Tracker & UDP Streamer
Captures camera (Local Webcam or IP Camera URL), tracks body pose & Superhero Punch gestures,
and streams UDP telemetry to Pygame.
"""

import sys
import time
import socket
import json
import math
import cv2
import numpy as np

# Try importing ultralytics
try:
    from ultralytics import YOLO
except ImportError:
    print("[Error] 'ultralytics' package not installed. Run: pip install ultralytics")
    sys.exit(1)

# UDP Settings
UDP_IP = "127.0.0.1"
UDP_PORT = 5005

# Default IP Camera URL or local index 0
DEFAULT_CAM = "http://192.168.20.103:8080/video"

def main():
    cam_source = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_CAM

    print(f"[YOLO Pose Tracker] Initializing UDP Socket -> {UDP_IP}:{UDP_PORT}...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    print("[YOLO Pose Tracker] Loading YOLOv8n-pose model...")
    model = YOLO('yolov8n-pose.pt')

    print(f"[YOLO Pose Tracker] Connecting to camera source: {cam_source}...")
    
    # Try connecting to specified source (IP camera or webcam index)
    try:
        source_idx = int(cam_source)
        cap = cv2.VideoCapture(source_idx)
    except ValueError:
        cap = cv2.VideoCapture(cam_source)

    if not cap.isOpened() and cam_source != "0":
        print(f"[Warning] Could not connect to '{cam_source}'. Falling back to local webcam (0)...")
        cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("[Error] Could not open any camera source!")
        sys.exit(1)

    print("\n=======================================================")
    print("  YOLO Pose Tracker (SUPERHERO PUNCH EDITION) Active!")
    print(f"  - Camera Source: {cam_source}")
    print("  - Lean Body Left / Right: Move Spaceship")
    print("  - 🥊 SUPERHERO PUNCH (Thrust Arm Forward/Out): Shoot Lasers!")
    print("  - 👏 POWER CLAP (Hands Together): Shoot Lasers!")
    print("  - Press 'q' or ESC in camera window to exit")
    print("=======================================================\n")

    norm_x = 0.5
    norm_y = 0.8
    shoot_active = False

    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            print("[Warning] Waiting for camera stream...")
            time.sleep(0.05)
            continue

        # Resize if stream is huge for faster inference
        if frame.shape[1] > 800:
            frame = cv2.resize(frame, (640, 480))

        # Flip horizontally for natural mirror feel if local webcam
        if isinstance(cam_source, int) or cam_source == "0":
            frame = cv2.flip(frame, 1)

        h, w, _ = frame.shape

        # Run YOLO Pose inference
        results = model(frame, verbose=False, conf=0.40)

        if results and len(results) > 0 and results[0].keypoints is not None:
            keypoints_data = results[0].keypoints.data
            if len(keypoints_data) > 0:
                # Keypoints index map:
                # 0: Nose, 5: L_Shoulder, 6: R_Shoulder, 7: L_Elbow, 8: R_Elbow, 9: L_Wrist, 10: R_Wrist
                kp = keypoints_data[0].cpu().numpy()

                l_shoulder = kp[5]
                r_shoulder = kp[6]
                l_elbow = kp[7]
                r_elbow = kp[8]
                l_wrist = kp[9]
                r_wrist = kp[10]

                # Check confidence of shoulders
                if l_shoulder[2] > 0.35 and r_shoulder[2] > 0.35:
                    shoulder_center_x = (l_shoulder[0] + r_shoulder[0]) / 2.0
                    shoulder_center_y = (l_shoulder[1] + r_shoulder[1]) / 2.0

                    shoulder_dist = math.hypot(r_shoulder[0] - l_shoulder[0], r_shoulder[1] - l_shoulder[1])
                    shoulder_dist = max(1.0, shoulder_dist)

                    # Normalize X position (0.0 to 1.0)
                    raw_norm_x = shoulder_center_x / float(w)
                    center_offset = raw_norm_x - 0.5
                    norm_x = max(0.05, min(0.95, 0.5 + center_offset * 1.8))

                    # Normalize Y position
                    norm_y = max(0.1, min(0.9, (shoulder_center_y / float(h)) * 1.2))

                    # --- SUPERHERO PUNCH, CLAP & JUMP BOMB GESTURE DETECTION ---
                    # 1. Arm Extension Ratio
                    l_arm_ext = math.hypot(l_wrist[0] - l_shoulder[0], l_wrist[1] - l_shoulder[1]) / shoulder_dist
                    r_arm_ext = math.hypot(r_wrist[0] - r_shoulder[0], r_wrist[1] - r_shoulder[1]) / shoulder_dist
                    wrist_dist = math.hypot(r_wrist[0] - l_wrist[0], r_wrist[1] - l_wrist[1]) / shoulder_dist

                    left_punch = (l_wrist[2] > 0.35 and l_arm_ext > 1.15)
                    right_punch = (r_wrist[2] > 0.35 and r_arm_ext > 1.15)
                    hands_clapped = (l_wrist[2] > 0.35 and r_wrist[2] > 0.35 and wrist_dist < 0.45)

                    shoot_active = left_punch or right_punch or hands_clapped

                    # 2. Both Hands Up OR Jump + Punch for SUPER BOMB
                    both_hands_up = (l_wrist[2] > 0.35 and r_wrist[2] > 0.35 and 
                                     l_wrist[1] < l_shoulder[1] - 15 and r_wrist[1] < r_shoulder[1] - 15)
                    
                    # Jump detection (shoulders elevated up high in frame)
                    is_jumping = (shoulder_center_y < h * 0.42)
                    jump_punch_bomb = is_jumping and (left_punch or right_punch or hands_clapped)

                    bomb_active = both_hands_up or jump_punch_bomb

                    # --- Visual Skeleton & Punch HUD Overlay ---
                    cv2.line(frame, (int(l_shoulder[0]), int(l_shoulder[1])), 
                             (int(r_shoulder[0]), int(r_shoulder[1])), (0, 255, 255), 3)
                    cv2.circle(frame, (int(shoulder_center_x), int(shoulder_center_y)), 8, (0, 255, 0), -1)

                    # Draw Left Arm & Punch Glow
                    if l_wrist[2] > 0.35:
                        l_color = (255, 0, 255) if bomb_active else ((0, 0, 255) if left_punch else (0, 240, 255))
                        cv2.line(frame, (int(l_shoulder[0]), int(l_shoulder[1])), (int(l_wrist[0]), int(l_wrist[1])), l_color, 4)
                        cv2.circle(frame, (int(l_wrist[0]), int(l_wrist[1])), 16 if bomb_active else 10, l_color, -1)

                    # Draw Right Arm & Punch Glow
                    if r_wrist[2] > 0.35:
                        r_color = (255, 0, 255) if bomb_active else ((0, 0, 255) if right_punch else (0, 240, 255))
                        cv2.line(frame, (int(r_shoulder[0]), int(r_shoulder[1])), (int(r_wrist[0]), int(r_wrist[1])), r_color, 4)
                        cv2.circle(frame, (int(r_wrist[0]), int(r_wrist[1])), 16 if bomb_active else 10, r_color, -1)

        # Transmit UDP JSON packet to Pygame game
        payload = {
            "x": float(norm_x),
            "y": float(norm_y),
            "shoot": bool(shoot_active),
            "bomb": bool(bomb_active),
            "time": time.time()
        }
        sock.sendto(json.dumps(payload).encode('utf-8'), (UDP_IP, UDP_PORT))

        # --- Draw HUD Overlay on Camera Window ---
        cv2.rectangle(frame, (10, h - 50), (w - 10, h - 10), (20, 20, 20), -1)
        gauge_x = int(10 + (w - 20) * norm_x)
        cv2.line(frame, (10, h - 30), (w - 10, h - 30), (100, 100, 100), 2)
        cv2.circle(frame, (gauge_x, h - 30), 8, (255, 255, 0), -1)

        if bomb_active:
            status_text = "💥 SUPER BOMB BLAST UNLEASHED! 💥"
            color = (255, 0, 255)
        else:
            status_text = f"CAM: {cam_source.split('/')[-1]} | PUNCH: {'YES 🥊' if shoot_active else 'NO'}"
            color = (0, 0, 255) if shoot_active else (0, 255, 255)

        cv2.putText(frame, status_text, (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2)

        cv2.imshow("YOLO Pose Tracker (Superhero Punch Control)", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q') or key == 27:  # ESC key
            break

    cap.release()
    cv2.destroyAllWindows()
    print("[YOLO Pose Tracker] Closed successfully.")

if __name__ == "__main__":
    main()
