import sys
import os
import time
import socket
import json
import math
import threading
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
# UDP Settings (Sends to Pygame on 5005 AND Web Server on 5006)
UDP_IP = "127.0.0.1"
UDP_PORTS = [5005, 5006]

# Target max processing rate: 10 FPS (100ms per frame)
TARGET_FPS = 10.0
PROCESS_INTERVAL = 1.0 / TARGET_FPS  # 0.100s = 100ms

# Default Camera (can be webcam 0, IP URL, or RTSP stream)
DEFAULT_CAM = "rtsp://192.168.1.114:554/live/11"


class LatestFrameReader:
    """
    Background worker thread continuously grabbing frames to drain camera/RTSP buffers.
    Ensures main inference loop ALWAYS receives the single freshest frame with zero lag.
    """
    def __init__(self, cap):
        self.cap = cap
        self.lock = threading.Lock()
        self.latest_frame = None
        self.running = True
        self.thread = threading.Thread(target=self._grab_loop, daemon=True)
        self.thread.start()

    def _grab_loop(self):
        while self.running and self.cap.isOpened():
            success, frame = self.cap.read()
            if success:
                with self.lock:
                    self.latest_frame = frame
            else:
                time.sleep(0.01)

    def get_latest(self):
        with self.lock:
            return self.latest_frame.copy() if self.latest_frame is not None else None

    def stop(self):
        self.running = False


from collections import deque

def main():
    cam_source = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_CAM

    print(f"[YOLO Pose Tracker] Initializing UDP Sockets -> {UDP_IP}:{UDP_PORTS}...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    print("[YOLO Pose Tracker] Loading YOLOv8n-pose model...")
    model = YOLO('yolov8n-pose.pt')

    print(f"[YOLO Pose Tracker] Connecting to camera source: {cam_source}...")
    
    # Enable TCP transport plus low-latency FFmpeg flags for RTSP streams.
    if str(cam_source).startswith("rtsp://"):
        os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = (
            "rtsp_transport;tcp|"
            "fflags;nobuffer|"
            "flags;low_delay|"
            "analyzeduration;0|"
            "probesize;32"
        )
        cap = cv2.VideoCapture(cam_source, cv2.CAP_FFMPEG)
    else:
        try:
            source_idx = int(cam_source)
            cap = cv2.VideoCapture(source_idx)
        except ValueError:
            cap = cv2.VideoCapture(cam_source)

    # Set low buffer size to minimize latency for real-time tracking
    try:
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    except Exception:
        pass

    if not cap.isOpened() and cam_source != "0":
        print(f"[Warning] Could not connect to '{cam_source}'. Falling back to local webcam (0)...")
        cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("[Error] Could not open any camera source!")
        sys.exit(1)

    # Start non-blocking frame grabber
    reader = LatestFrameReader(cap)

    print("\n=======================================================")
    print("  🚀 YOLO Pose Tracker (DOUBLE-JUMP BOMB EDITION) Active!")
    print(f"  - Camera Source: {cam_source}")
    print("  - Processing Rate: Max 10 FPS (100ms per frame, zero latency)")
    print("  - 🏃 Lean Body Left / Right: Steer Spaceship")
    print("  - 💥 EVERY 2ND JUMP (Body Up): SUPER BOMB BLAST!")
    print("  - 🙌 BOTH HANDS UP: FIRE LASERS")
    print("  - 'f': Toggle Camera Mirror Flip (Currently ON)")
    print("  - Press 'q' or ESC in camera window to exit")
    print("=======================================================\n")

    norm_x = 0.5
    norm_y = 0.8
    flip_horizontal = True

    # Dynamic relative motion tracker (Sliding window of recent Y positions)
    history_y = deque(maxlen=10)  # 1 second history
    prev_body_y = None
    prev2_body_y = None
    jump_state = "READY"
    jump_latch_counter = 0
    bomb_latch_counter = 0

    # Every-2nd-jump -> Super Bomb state (velocity phase machine)
    jump_phase = 0             # 0=idle, 1=rising, 2=falling
    jump_streak = 0            # count of jumps; every 2nd jump fires the bomb
    JUMP_PAIR_TIMEOUT = 1.6    # max seconds between the two jumps of a bomb pair
    last_jump_time = 0.0       # landing time of the last counted jump
    BOMB_COOLDOWN = 5.0        # minimum seconds between super bombs
    last_bomb_time = 0.0       # time the last super bomb fired
    MIN_BOMB_ELEV = 0.08       # body center must lift >= 8% of shoulder width at the apex
    LEAN_TILT_LIMIT = 0.35     # shoulders tilted >= 35% of width => sideways lean, not a jump
    jump_peak_elevation = 0.0
    jump_phase_started_at = 0.0

    while True:
        loop_start = time.time()

        # Fetch the freshest camera frame (drops all backlog)
        raw_frame = reader.get_latest()
        if raw_frame is None:
            time.sleep(0.01)
            continue

        frame = raw_frame

        # Resize if stream is huge for faster inference
        if frame.shape[1] > 800:
            frame = cv2.resize(frame, (640, 480))

        # Mirror flip horizontally so moving left in reality moves left on camera/screen
        if flip_horizontal:
            frame = cv2.flip(frame, 1)

        h, w, _ = frame.shape

        # Run YOLO Pose inference at max 10 FPS
        results = model(frame, verbose=False, conf=0.40)

        shoot_active = False
        bomb_active = False
        is_jumping = False
        rel_elevation = 0.0
        rel_vel = 0.0

        if results and len(results) > 0 and results[0].keypoints is not None:
            keypoints_data = results[0].keypoints.data
            if len(keypoints_data) > 0:
                # Keypoints index map:
                # 0: Nose, 5: L_Shoulder, 6: R_Shoulder, 9: L_Wrist, 10: R_Wrist, 11: L_Hip, 12: R_Hip
                kp = keypoints_data[0].cpu().numpy()

                nose = kp[0]
                l_shoulder = kp[5]
                r_shoulder = kp[6]
                l_wrist = kp[9]
                r_wrist = kp[10]
                l_hip = kp[11]
                r_hip = kp[12]

                # Check confidence of shoulders or nose
                if l_shoulder[2] > 0.35 and r_shoulder[2] > 0.35:
                    shoulder_center_x = (l_shoulder[0] + r_shoulder[0]) / 2.0
                    shoulder_center_y = (l_shoulder[1] + r_shoulder[1]) / 2.0

                    shoulder_dist = math.hypot(r_shoulder[0] - l_shoulder[0], r_shoulder[1] - l_shoulder[1])
                    shoulder_dist = max(15.0, shoulder_dist)

                    # Normalize X position (0.0 to 1.0) for horizontal steering
                    raw_norm_x = shoulder_center_x / float(w)
                    center_offset = raw_norm_x - 0.5
                    norm_x = max(0.05, min(0.95, 0.5 + center_offset * 1.8))
                    norm_y = max(0.1, min(0.9, (shoulder_center_y / float(h))))

                    # --- DYNAMIC RELATIVE JUMP DETECTION ---
                    # Track the BODY center (hips + shoulders), NOT the head. Hips rise the most
                    # during a jump and are immune to head-bobbing, so jumps register the same
                    # for short kids and tall adults. All distances are normalized by the
                    # person's own shoulder width, making thresholds height/distance-independent.
                    hip_ok = l_hip[2] > 0.35 and r_hip[2] > 0.35
                    if hip_ok:
                        hip_center_y = (l_hip[1] + r_hip[1]) / 2.0
                        body_y = hip_center_y * 0.6 + shoulder_center_y * 0.4
                    else:
                        body_y = shoulder_center_y
                    history_y.append(body_y)

                    if len(history_y) >= 3:
                        # Recent standing reference (70th percentile = lowest recent position)
                        ref_standing_y = np.percentile(list(history_y), 70)

                        # Relative upward elevation (fraction of shoulder width)
                        rel_elevation = (ref_standing_y - body_y) / shoulder_dist

                        # Relative upward velocity, smoothed over 2 frames (200ms)
                        if prev2_body_y is not None:
                            rel_vel = (prev2_body_y - body_y) / shoulder_dist
                        else:
                            rel_vel = 0.0

                        # Shoulder tilt: |L-R shoulder Y| / shoulder width. ~0 when level
                        # (standing or jumping); large when leaning sideways to steer. Used
                        # to reject sideways leans as fake jumps.
                        shoulder_tilt = abs(l_shoulder[1] - r_shoulder[1]) / shoulder_dist

                        # --- JUMP DETECTION (drives the bomb counter & game-over restart) ---
                        # A jump needs a real rise: either a fast rise (velocity AND elevation
                        # together, so lean/keypoint jitter -- where the two are out of phase --
                        # doesn't count) or a large elevation gain. Never while the shoulders
                        # are tilted sideways (a lean, not a jump). This only sets is_jumping;
                        # lasers are fired by the hands-up gesture further below.
                        if jump_state == "READY":
                            if shoulder_tilt < LEAN_TILT_LIMIT and (
                                    (rel_vel >= 0.12 and rel_elevation >= 0.08) or
                                    rel_elevation >= 0.20):
                                jump_state = "JUMPING"
                                jump_latch_counter = 3  # Hold active for 300ms
                        elif jump_state == "JUMPING":
                            if rel_elevation < 0.03 and rel_vel <= 0:
                                jump_state = "READY"
                            elif jump_latch_counter <= 0:
                                jump_state = "READY"

                        # --- EVERY 2ND JUMP -> SUPER BOMB (velocity phase machine) ---
                        # A jump is counted ONLY when the whole cycle completes:
                        #   takeoff (rising) -> apex (lifted) -> landing (falling).
                        # Counting at landing (not takeoff) + requiring real elevation at
                        # the apex means sideways lean or keypoint jitter -- which make
                        # velocity spikes but never lift the body above the standing
                        # reference -- abort harmlessly and never touch the pair counter.
                        now = time.time()
                        if jump_phase == 0:   # idle
                            if shoulder_tilt < LEAN_TILT_LIMIT and (
                                    (rel_vel >= 0.07 and rel_elevation >= 0.04) or
                                    rel_elevation >= MIN_BOMB_ELEV):
                                jump_phase = 1
                                jump_peak_elevation = max(0.0, rel_elevation)
                                jump_phase_started_at = now
                        elif jump_phase == 1:   # rising
                            jump_peak_elevation = max(jump_peak_elevation, rel_elevation)
                            if shoulder_tilt >= LEAN_TILT_LIMIT or now - jump_phase_started_at > 1.0:
                                jump_phase = 0   # lean/jitter/stale phase -> abort
                            elif rel_vel <= 0.02:
                                if jump_peak_elevation >= MIN_BOMB_ELEV:
                                    jump_phase = 2   # genuine lift-off -> now falling/landing
                                else:
                                    jump_phase = 0   # no real lift -> abort
                        elif jump_phase == 2:   # falling
                            jump_peak_elevation = max(jump_peak_elevation, rel_elevation)
                            returned_to_baseline = rel_elevation <= 0.04 and rel_vel <= 0.03
                            falling_from_peak = rel_vel <= -0.06 and rel_elevation <= jump_peak_elevation - 0.03
                            stale_landing = now - jump_phase_started_at > 1.2 and rel_elevation <= 0.06
                            if returned_to_baseline or falling_from_peak or stale_landing:
                                jump_phase = 0
                                # IGNORE every jump during the 5s super-bomb cooldown: a
                                # double jump in that window must not fire, and must not be
                                # banked toward the next pair either.
                                if now - last_bomb_time < BOMB_COOLDOWN:
                                    jump_streak = 0
                                else:
                                    # Too much time since the last jump? Start a new pair.
                                    if now - last_jump_time > JUMP_PAIR_TIMEOUT:
                                        jump_streak = 0
                                    jump_streak += 1
                                    last_jump_time = now
                                    if jump_streak >= 2:
                                        bomb_latch_counter = 3   # EVERY 2ND JUMP -> BOMB
                                        jump_streak = 0
                                        last_bomb_time = now
                                        print("[YOLO Pose Tracker] 💥 SUPER BOMB (2 JUMPS)!")
                            elif now - jump_phase_started_at > 1.5:
                                jump_phase = 0

                    prev2_body_y = prev_body_y
                    prev_body_y = body_y

                    if jump_latch_counter > 0:
                        is_jumping = True
                        jump_latch_counter -= 1

                    if bomb_latch_counter > 0:
                        bomb_active = True
                        bomb_latch_counter -= 1

                    # Both hands up -> FIRE LASERS (reliable shoot gesture, sized to the player
                    # so it works the same for short kids and tall adults)
                    raise_dist = max(12, shoulder_dist * 0.12)
                    both_hands_up = (l_wrist[2] > 0.35 and r_wrist[2] > 0.35 and
                                     l_wrist[1] < l_shoulder[1] - raise_dist and
                                     r_wrist[1] < r_shoulder[1] - raise_dist)
                    if both_hands_up:
                        shoot_active = True

                    # --- Visual Overlay ---
                    # Shoulder bar
                    cv2.line(frame, (int(l_shoulder[0]), int(l_shoulder[1])), 
                             (int(r_shoulder[0]), int(r_shoulder[1])), (0, 255, 255), 3)
                    
                    # Body center / Jump marker
                    center_color = (255, 0, 255) if bomb_active else ((0, 255, 128) if shoot_active else (0, 240, 255))
                    center_radius = 18 if (is_jumping or bomb_active or shoot_active) else 9
                    cv2.circle(frame, (int(shoulder_center_x), int(shoulder_center_y)), center_radius, center_color, -1)

                    if bomb_active:
                        cv2.putText(frame, "💥 SUPER BOMB (2 JUMPS)! 💥", (int(shoulder_center_x) - 130, int(shoulder_center_y) - 25),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.62, (255, 0, 255), 2)
                    elif shoot_active:
                        cv2.putText(frame, "🙌 HANDS UP -> FIRING!", (int(shoulder_center_x) - 105, int(shoulder_center_y) - 25),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.62, (0, 255, 128), 2)
                    elif is_jumping:
                        cv2.putText(frame, "🦘 JUMP (2 = BOMB)", (int(shoulder_center_x) - 105, int(shoulder_center_y) - 25),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.62, (0, 240, 255), 2)

        # Transmit UDP JSON packet to Pygame game (port 5005) & Web Server (port 5006)
        payload = {
            "x": float(norm_x),
            "y": float(norm_y),
            "shoot": bool(shoot_active),                  # both hands up -> fire lasers
            "jump": bool(is_jumping),
            "restart": bool(is_jumping or bomb_active),
            "bomb": bool(bomb_active),                    # every 2nd jump -> super bomb
            "time": time.time()
        }
        msg_bytes = json.dumps(payload).encode('utf-8')
        for port in UDP_PORTS:
            try:
                sock.sendto(msg_bytes, (UDP_IP, port))
            except Exception:
                pass

        # --- Draw HUD Overlay on Camera Window ---
        cv2.rectangle(frame, (10, h - 50), (w - 10, h - 10), (20, 20, 20), -1)
        gauge_x = int(10 + (w - 20) * norm_x)
        cv2.line(frame, (10, h - 30), (w - 10, h - 30), (100, 100, 100), 2)
        cv2.circle(frame, (gauge_x, h - 30), 8, (255, 255, 0), -1)

        if bomb_active:
            status_text = "💥 SUPER BOMB (2 JUMPS)! 💥"
            color = (255, 0, 255)
        elif shoot_active:
            status_text = "🙌 HANDS UP -> FIRING LASERS! 🚀"
            color = (0, 255, 128)
        elif is_jumping:
            status_text = "🦘 JUMP DETECTED (EVERY 2ND JUMP = BOMB)"
            color = (0, 240, 255)
        else:
            cooldown_left = BOMB_COOLDOWN - (time.time() - last_bomb_time)
            flip_str = "FLIP: ON" if flip_horizontal else "FLIP: OFF"
            if cooldown_left > 0:
                status_text = f"BOMB COOLDOWN {cooldown_left:.1f}s (JUMPS IGNORED)"
                color = (255, 210, 0)
            else:
                status_text = f"10 FPS | JUMP COUNT {jump_streak}/2 | 2 JUMPS = BOMB | {flip_str} ('f')"
                color = (200, 230, 255)

        cv2.putText(frame, status_text, (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.58, color, 2)

        cv2.imshow("YOLO Pose Tracker (10 FPS Jump Edition)", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q') or key == 27:  # ESC key
            break
        elif key == ord('f') or key == ord('F'):
            flip_horizontal = not flip_horizontal
            print(f"[YOLO Pose Tracker] Mirror flip toggled: {'ON' if flip_horizontal else 'OFF'}")

        # Enforce exact 10 FPS (100ms per frame cycle)
        elapsed = time.time() - loop_start
        sleep_needed = max(0.001, PROCESS_INTERVAL - elapsed)
        time.sleep(sleep_needed)

    reader.stop()
    cap.release()
    cv2.destroyAllWindows()
    print("[YOLO Pose Tracker] Closed successfully.")


if __name__ == "__main__":
    main()
