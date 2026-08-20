#!/usr/bin/env python3
"""
SpaceShip Dodge: Pose Edition
Main Pygame application with non-blocking UDP receiver for YOLO Pose tracking.
"""

import sys
import math
import random
import socket
import json
import threading
import time
import shutil
import subprocess
import pygame
import numpy as np

# --- Configuration & Constants ---
SCREEN_WIDTH = 1000
SCREEN_HEIGHT = 750
FPS = 60

UDP_IP = "127.0.0.1"
UDP_PORT = 5005

# --- Sound Effects Generator (Procedural 8-Bit Audio) ---
class SoundEffects:
    def __init__(self):
        self.enabled = False
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            self.enabled = True
            self.laser = self._make_laser()
            self.explosion = self._make_explosion()
            self.hit = self._make_hit()
            self.damage = self._make_damage()
            self.bomb = self._make_bomb()
            print("[Audio] Sound engine active!")
        except Exception as e:
            print(f"[Audio Warning] Sound disabled: {e}")

    def _make_laser(self):
        sr = 44100
        t = np.linspace(0, 0.11, int(sr * 0.11), False)
        freq = np.linspace(950, 220, len(t))
        wave = np.sin(2 * np.pi * freq * t) * np.exp(-t * 18)
        audio = (wave * 12000).astype(np.int16)
        return pygame.sndarray.make_sound(np.column_stack((audio, audio)))

    def _make_explosion(self):
        sr = 44100
        t = np.linspace(0, 0.35, int(sr * 0.35), False)
        noise = np.random.uniform(-1, 1, len(t))
        sub = np.sin(2 * np.pi * 55 * t)
        wave = (noise * 0.7 + sub * 0.3) * np.exp(-t * 8)
        audio = (wave * 16000).astype(np.int16)
        return pygame.sndarray.make_sound(np.column_stack((audio, audio)))

    def _make_hit(self):
        sr = 44100
        t = np.linspace(0, 0.08, int(sr * 0.08), False)
        wave = np.sin(2 * np.pi * 1200 * t) * np.exp(-t * 40)
        audio = (wave * 10000).astype(np.int16)
        return pygame.sndarray.make_sound(np.column_stack((audio, audio)))

    def _make_damage(self):
        sr = 44100
        t = np.linspace(0, 0.25, int(sr * 0.25), False)
        wave = (np.sin(2 * np.pi * 110 * t) + np.sin(2 * np.pi * 85 * t)) * np.exp(-t * 6)
        audio = (wave * 18000).astype(np.int16)
        return pygame.sndarray.make_sound(np.column_stack((audio, audio)))

    def _make_bomb(self):
        sr = 44100
        t = np.linspace(0, 0.6, int(sr * 0.6), False)
        noise = np.random.uniform(-1, 1, len(t))
        sub = np.sin(2 * np.pi * 40 * t) + np.sin(2 * np.pi * 65 * t)
        wave = (noise * 0.5 + sub * 0.5) * np.exp(-t * 4)
        audio = (wave * 20000).astype(np.int16)
        return pygame.sndarray.make_sound(np.column_stack((audio, audio)))

    def play_laser(self):
        if self.enabled: self.laser.play()

    def play_explosion(self):
        if self.enabled: self.explosion.play()

    def play_hit(self):
        if self.enabled: self.hit.play()

    def play_damage(self):
        if self.enabled: self.damage.play()

    def play_bomb(self):
        if self.enabled: self.bomb.play()

class ScoreAnnouncer:
    """
    Speaks score milestones (10,000, 20,000, ...) via whatever TTS is available.
    Tries pyttsx3, then the espeak-ng command (Linux), then `say` (macOS).
    All speaking is fire-and-forget so it never blocks the game loop.
    """
    def __init__(self):
        self.last_milestone = 0
        self.backend = self._detect_backend()
        if self.backend:
            print(f"[TTS] Score announcer ready (backend: {self.backend})")
        else:
            print("[TTS] No TTS backend found - score announcements disabled")

    def _detect_backend(self):
        try:
            import pyttsx3
            self._pyttsx3 = pyttsx3.init()
            return "pyttsx3"
        except Exception:
            pass
        if shutil.which("espeak-ng"):
            return "espeak-ng"
        if sys.platform == "darwin" and shutil.which("say"):
            return "say"
        return None

    def check(self, score):
        """Call each frame; announces when the score crosses a new 10,000 milestone."""
        milestone = int(score) // 10000
        if milestone > self.last_milestone and milestone >= 1:
            self.last_milestone = milestone
            self.speak(str(milestone * 10000))

    def speak(self, text):
        if self.backend == "pyttsx3":
            threading.Thread(target=self._speak_pyttsx3, args=(text,), daemon=True).start()
        elif self.backend == "espeak-ng":
            subprocess.Popen(["espeak-ng", "-s", "165", "-a", "150", text],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        elif self.backend == "say":
            subprocess.Popen(["say", text],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def apply_health_milestones(player, score, last_milestone):
    """Return half health on each 5000-point milestone reached."""
    milestone = score // 5000
    if milestone <= last_milestone:
        return last_milestone

    for _ in range(last_milestone + 1, milestone + 1):
        player.health = min(player.max_health, player.health + player.max_health // 2)

    return milestone

    def _speak_pyttsx3(self, text):
        try:
            self._pyttsx3.say(text)
            self._pyttsx3.runAndWait()
        except Exception:
            pass

class Shockwave:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.radius = 10
        self.max_radius = 900
        self.speed = 35

    def update(self):
        self.radius += self.speed

    def draw(self, surface):
        if self.radius < self.max_radius:
            width = max(2, int(16 * (1.0 - self.radius / self.max_radius)))
            pygame.draw.circle(surface, (255, 0, 255), (int(self.x), int(self.y)), int(self.radius), width=width)
            pygame.draw.circle(surface, (0, 240, 255), (int(self.x), int(self.y)), int(self.radius * 0.85), width=max(1, width//2))

# Colors (Vibrant Futuristic Palette)
COLOR_BG = (10, 12, 24)
COLOR_WHITE = (240, 245, 255)
COLOR_CYAN = (0, 240, 255)
COLOR_MAGENTA = (255, 0, 128)
COLOR_YELLOW = (255, 220, 0)
COLOR_RED = (255, 60, 60)
COLOR_GREEN = (0, 255, 128)
COLOR_HUD_BG = (20, 25, 45, 180)

# --- Global UDP Receiver State ---
udp_state = {
    "norm_x": 0.5,       # Normalized position 0.0 (left) to 1.0 (right)
    "norm_y": 0.8,       # Normalized position 0.0 (top) to 1.0 (bottom)
    "shoot": False,
    "jump": False,
    "restart": False,
    "bomb": False,
    "last_packet_time": 0.0,
    "active": False
}

def udp_listener_thread():
    """Background thread listening for incoming UDP telemetry packets."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    except Exception:
        pass
    try:
        sock.bind((UDP_IP, UDP_PORT))
        sock.settimeout(0.5)
        print(f"[UDP Listener] Listening on {UDP_IP}:{UDP_PORT}...")
    except Exception as e:
        print(f"[UDP Listener Error] Could not bind to {UDP_IP}:{UDP_PORT} -> {e}")
        return

    try:
        while True:
            try:
                data, _ = sock.recvfrom(1024)
                payload = json.loads(data.decode('utf-8'))
                udp_state["norm_x"] = payload.get("x", udp_state["norm_x"])
                udp_state["norm_y"] = payload.get("y", udp_state["norm_y"])
                udp_state["shoot"] = payload.get("shoot", False)
                udp_state["jump"] = payload.get("jump", False)
                udp_state["restart"] = payload.get("restart", False)
                udp_state["bomb"] = payload.get("bomb", False)
                udp_state["last_packet_time"] = time.time()
                udp_state["active"] = True
            except socket.timeout:
                if time.time() - udp_state["last_packet_time"] > 2.0:
                    udp_state["active"] = False
            except Exception:
                pass
    finally:
        sock.close()

# --- Game Entities ---

class Star:
    def __init__(self):
        self.x = random.randint(0, SCREEN_WIDTH)
        self.y = random.randint(0, SCREEN_HEIGHT)
        self.speed = random.uniform(0.5, 3.5)
        self.size = random.uniform(1.0, 3.0)
        self.brightness = random.randint(120, 255)

    def update(self):
        self.y += self.speed
        if self.y > SCREEN_HEIGHT:
            self.y = 0
            self.x = random.randint(0, SCREEN_WIDTH)

    def draw(self, surface):
        c = max(0, min(255, int(self.brightness)))
        c_blue = max(0, min(255, int(c * 1.1)))
        pygame.draw.circle(surface, (c, c, c_blue), (int(self.x), int(self.y)), int(self.size))

class Particle:
    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        self.vx = random.uniform(-4, 4)
        self.vy = random.uniform(-4, 4)
        self.radius = random.uniform(2, 6)
        self.color = color
        self.life = 1.0  # 1.0 to 0.0
        self.decay = random.uniform(0.02, 0.05)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.life -= self.decay

    def draw(self, surface):
        if self.life > 0:
            r = max(1, int(self.radius * self.life))
            alpha_color = tuple(max(0, min(255, int(c * self.life))) for c in self.color)
            pygame.draw.circle(surface, alpha_color, (int(self.x), int(self.y)), r)

class Laser:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.speed = 14
        self.width = 4
        self.height = 18

    def update(self):
        self.y -= self.speed

    def draw(self, surface):
        # Outer Glow
        glow_rect = pygame.Rect(self.x - self.width, self.y - 2, self.width * 3, self.height + 4)
        pygame.draw.rect(surface, (0, 180, 255), glow_rect, border_radius=4)
        # Core Laser
        core_rect = pygame.Rect(self.x, self.y, self.width, self.height)
        pygame.draw.rect(surface, (240, 255, 255), core_rect, border_radius=2)

class Asteroid:
    def __init__(self, difficulty=1.0):
        self.radius = random.randint(22, 48)
        self.x = random.randint(self.radius, SCREEN_WIDTH - self.radius)
        self.y = -self.radius * 2
        # Slow and smooth falling speed for comfortable reaction time
        base_speed = random.uniform(1.2, 2.4)
        speed_mult = 1.0 + min(0.8, (difficulty - 1.0) * 0.08)
        self.speed = base_speed * speed_mult
        self.rotation = random.uniform(0, 360)
        self.rot_speed = random.uniform(-2.0, 2.0)
        self.hp = max(1, int(self.radius / 16))
        
        # 4 Colorful Kid-Friendly Types
        self.kind = random.choice(["crystal", "ufo", "fireball", "space_rock"])
        self.color = random.choice([
            (255, 0, 180),   # Neon Pink
            (0, 240, 255),   # Electric Cyan
            (0, 255, 128),   # Emerald Green
            (255, 215, 0),   # Gold / Sunburst
            (255, 80, 0),    # Fiery Orange
            (180, 90, 255)   # Cosmic Purple
        ])
        
        # Jagged points for space rocks
        self.num_points = random.randint(7, 10)
        self.points = []
        for i in range(self.num_points):
            angle = (2 * math.pi / self.num_points) * i
            dist = self.radius * random.uniform(0.75, 1.25)
            self.points.append((dist * math.cos(angle), dist * math.sin(angle)))

    def update(self, particles=None):
        self.y += self.speed
        self.rotation += self.rot_speed

        # Emit trailing particles for fireballs, UFOs, and glowing crystals
        if particles is not None and random.random() < 0.6:
            if self.kind == "fireball":
                particles.append(Particle(self.x + random.uniform(-6, 6), self.y - 10, (255, random.randint(100, 220), 0)))
            elif self.kind == "crystal":
                particles.append(Particle(self.x + random.uniform(-10, 10), self.y + random.uniform(-10, 10), self.color))
            elif self.kind == "ufo":
                particles.append(Particle(self.x + random.uniform(-12, 12), self.y + 8, (0, 240, 255)))

    def draw(self, surface):
        rad = math.radians(self.rotation)
        cos_a, sin_a = math.cos(rad), math.sin(rad)

        if self.kind == "crystal":
            # Shiny Diamond Crystal
            points = [
                (self.x, self.y - self.radius),
                (self.x + self.radius * 0.7, self.y - self.radius * 0.2),
                (self.x + self.radius * 0.6, self.y + self.radius * 0.7),
                (self.x, self.y + self.radius),
                (self.x - self.radius * 0.6, self.y + self.radius * 0.7),
                (self.x - self.radius * 0.7, self.y - self.radius * 0.2)
            ]
            # Base Crystal
            pygame.draw.polygon(surface, self.color, points)
            # Inner Facet Lines
            pygame.draw.polygon(surface, (255, 255, 255), points, width=2)
            pygame.draw.line(surface, (255, 255, 255), (self.x, self.y - self.radius), (self.x, self.y + self.radius), 2)

        elif self.kind == "ufo":
            # Cute Alien Flying Saucer
            r = self.radius
            # Glowing Saucer Base
            saucer_rect = pygame.Rect(self.x - r, self.y - r*0.4, r*2, r*0.8)
            pygame.draw.ellipse(surface, (40, 60, 90), saucer_rect)
            pygame.draw.ellipse(surface, self.color, saucer_rect, width=3)
            # Glowing Glass Dome
            dome_rect = pygame.Rect(self.x - r*0.5, self.y - r*0.8, r, r*0.8)
            pygame.draw.ellipse(surface, (0, 240, 255), dome_rect)
            pygame.draw.ellipse(surface, (240, 255, 255), dome_rect, width=2)
            # Blinking Rim Lights
            for angle_deg in [0, 45, 90, 135, 180]:
                lx = self.x + (r * 0.8) * math.cos(math.radians(angle_deg + self.rotation))
                ly = self.y + (r * 0.3) * math.sin(math.radians(angle_deg + self.rotation))
                pygame.draw.circle(surface, (255, 230, 0), (int(lx), int(ly)), 3)

        elif self.kind == "fireball":
            # Fiery Meteor Core
            r = self.radius
            # Outer Fire Glow
            pygame.draw.circle(surface, (255, 100, 0), (int(self.x), int(self.y)), int(r))
            # Inner Flame Core
            pygame.draw.circle(surface, (255, 230, 50), (int(self.x), int(self.y)), int(r * 0.6))
            pygame.draw.circle(surface, (255, 255, 255), (int(self.x), int(self.y)), int(r * 0.3))

        else:  # Space Rock with Neon Glow
            transformed = []
            for px, py in self.points:
                rx = px * cos_a - py * sin_a + self.x
                ry = px * sin_a + py * cos_a + self.y
                transformed.append((rx, ry))

            # Draw Neon Space Rock Base & Outline
            dark_c = (int(self.color[0]*0.25), int(self.color[1]*0.25), int(self.color[2]*0.25))
            pygame.draw.polygon(surface, dark_c, transformed)
            pygame.draw.polygon(surface, self.color, transformed, width=3)

PLAYER_Y = int(SCREEN_HEIGHT * 0.88)

class Player:
    def __init__(self):
        self.x = SCREEN_WIDTH // 2
        self.y = PLAYER_Y
        self.target_x = self.x
        self.radius = 24
        self.health = 100
        self.max_health = 100
        self.shoot_cooldown = 0

    def update(self, norm_x, norm_y, is_udp):
        # Target horizontal interpolation (Smooth Lerping)
        if is_udp:
            self.target_x = norm_x * SCREEN_WIDTH
        
        # Clamp horizontal target
        self.target_x = max(self.radius, min(SCREEN_WIDTH - self.radius, self.target_x))

        # Smooth horizontal movement (Y position locked at bottom)
        self.x += (self.target_x - self.x) * 0.18
        self.y = PLAYER_Y

        if self.shoot_cooldown > 0:
            self.shoot_cooldown -= 1

    def draw(self, surface, particles):
        # Thruster particle effect
        for _ in range(2):
            particles.append(Particle(self.x + random.uniform(-6, 6), self.y + 22, (255, random.randint(100, 200), 50)))

        # Ship Body Polygons
        nose = (self.x, self.y - 28)
        left_wing = (self.x - 26, self.y + 20)
        left_inner = (self.x - 10, self.y + 12)
        right_inner = (self.x + 10, self.y + 12)
        right_wing = (self.x + 26, self.y + 20)

        # Glow Layer
        glow_points = [(nose[0], nose[1]-4), (left_wing[0]-4, left_wing[1]+4), (right_wing[0]+4, right_wing[1]+4)]
        pygame.draw.polygon(surface, (0, 150, 255), glow_points, width=4)

        # Main Ship Structure
        pygame.draw.polygon(surface, (20, 30, 50), [nose, left_wing, left_inner, right_inner, right_wing])
        pygame.draw.polygon(surface, COLOR_CYAN, [nose, left_wing, left_inner, right_inner, right_wing], width=2)

        # Cockpit Canopy
        cockpit = [(self.x, self.y - 14), (self.x - 6, self.y + 2), (self.x + 6, self.y + 2)]
        pygame.draw.polygon(surface, COLOR_MAGENTA, cockpit)

# --- Main Game Loop ---

def main():
    pygame.init()
    pygame.font.init()
    sound_fx = SoundEffects()
    announcer = ScoreAnnouncer()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("SpaceShip Dodge: YOLO Pose & Keyboard Edition")
    clock = pygame.time.Clock()

    font_large = pygame.font.SysFont("monospace", 42, bold=True)
    font_medium = pygame.font.SysFont("monospace", 24, bold=True)
    font_small = pygame.font.SysFont("monospace", 16, bold=True)

    # Start UDP Thread
    udp_thread = threading.Thread(target=udp_listener_thread, daemon=True)
    udp_thread.start()

    # Game Objects
    stars = [Star() for _ in range(90)]
    particles = []
    lasers = []
    asteroids = []
    shockwaves = []

    player = Player()

    score = 0
    game_over = False
    game_over_started_at = None
    spawn_timer = 0
    bomb_cooldown = 0
    health_milestone = 0

    print("[Game Started] Use Arrow Keys or launch 'python pose_tracker.py' for body control!")

    running = True
    while running:
        clock.tick(FPS)
        spawn_timer += 1

        # --- Event Handling ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_r and game_over:
                    # Restart Game
                    if game_over_started_at is not None and time.time() - game_over_started_at >= 5.0:
                        player = Player()
                        asteroids.clear()
                        lasers.clear()
                        particles.clear()
                        shockwaves.clear()
                        score = 0
                        bomb_cooldown = 0
                        game_over = False
                        game_over_started_at = None
                        announcer.last_milestone = 0
                        health_milestone = 0

        # --- Input Processing ---
        keys = pygame.key.get_pressed()
        is_udp = udp_state["active"]

        # Gesture Restart Check (Jump / Shoot / Raise Hands on Game Over)
        if game_over:
            if game_over_started_at is None:
                game_over_started_at = time.time()
            if time.time() - game_over_started_at >= 5.0 and is_udp:
                if udp_state.get("jump") or udp_state.get("restart") or udp_state.get("shoot") or udp_state.get("bomb"):
                    # Restart Game Immediately
                    player = Player()
                    asteroids.clear()
                    lasers.clear()
                    particles.clear()
                    shockwaves.clear()
                    score = 0
                    bomb_cooldown = 0
                    game_over = False
                    game_over_started_at = None
                    announcer.last_milestone = 0
                    health_milestone = 0
                    udp_state["shoot"] = False
                    udp_state["jump"] = False
                    udp_state["restart"] = False
                    udp_state["bomb"] = False

        if not is_udp and not game_over:
            # Keyboard controls fallback (Horizontal Only)
            move_speed = 9.0
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                player.target_x -= move_speed
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                player.target_x += move_speed

        # Shoot Trigger (Keyboard or UDP)
        should_shoot = keys[pygame.K_SPACE] or (is_udp and udp_state["shoot"])
        if should_shoot and player.shoot_cooldown == 0 and not game_over:
            lasers.append(Laser(player.x - 12, player.y - 15))
            lasers.append(Laser(player.x + 12, player.y - 15))
            player.shoot_cooldown = 12
            sound_fx.play_laser()

        # Super Bomb Trigger (Keyboard 'B' / Shift OR UDP Double Jump / Both Hands Up)
        should_bomb = keys[pygame.K_b] or keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT] or (is_udp and udp_state["bomb"])
        if should_bomb and bomb_cooldown == 0 and not game_over:
            bomb_cooldown = 90  # 1.5 sec cooldown
            shockwaves.append(Shockwave(player.x, player.y))
            sound_fx.play_bomb()

            # Destroy all active obstacles on screen with bonus points
            for asteroid in asteroids[:]:
                score += int(asteroid.radius * 3) + 30
                for _ in range(20):
                    particles.append(Particle(asteroid.x, asteroid.y, COLOR_MAGENTA))
                asteroids.remove(asteroid)

        if bomb_cooldown > 0:
            bomb_cooldown -= 1

        # --- Logic Updates ---
        for star in stars:
            star.update()

        if not game_over:
            # Survival Score (1 point every 6 frames / ~10 points per sec)
            if spawn_timer % 6 == 0:
                score += 1

            # Update Player
            player.update(udp_state["norm_x"], udp_state["norm_y"], is_udp)

            # Spawn Asteroids
            difficulty = 1.0 + (score / 700)
            spawn_interval = max(32, int(65 / difficulty))
            if spawn_timer >= spawn_interval:
                asteroids.append(Asteroid(difficulty))
                spawn_timer = 0

            # Update Lasers
            for laser in lasers[:]:
                laser.update()
                if laser.y < -30:
                    lasers.remove(laser)

            # Update Asteroids & Collisions
            for asteroid in asteroids[:]:
                asteroid.update(particles)

                # Check Laser Collisions
                for laser in lasers[:]:
                    dist = math.hypot(laser.x - asteroid.x, laser.y - asteroid.y)
                    if dist < asteroid.radius + 6:
                        if laser in lasers:
                            lasers.remove(laser)
                        asteroid.hp -= 1
                        sound_fx.play_hit()

                        # Hit Particles
                        for _ in range(6):
                            particles.append(Particle(laser.x, laser.y, COLOR_YELLOW))

                        if asteroid.hp <= 0:
                            # Destruction Bonus
                            score += int(asteroid.radius * 3) + 20
                            sound_fx.play_explosion()
                            for _ in range(18):
                                particles.append(Particle(asteroid.x, asteroid.y, COLOR_CYAN))
                            if asteroid in asteroids:
                                asteroids.remove(asteroid)
                            break

                # Check Player Collision
                dist_p = math.hypot(player.x - asteroid.x, player.y - asteroid.y)
                if dist_p < player.radius + asteroid.radius * 0.8:
                    player.health -= 25
                    sound_fx.play_damage()
                    for _ in range(25):
                        particles.append(Particle(player.x, player.y, COLOR_RED))
                    if asteroid in asteroids:
                        asteroids.remove(asteroid)

                    if player.health <= 0:
                        player.health = 0
                        game_over = True
                        if game_over_started_at is None:
                            game_over_started_at = time.time()

                # Remove off-screen asteroids (Dodge Bonus)
                elif asteroid.y > SCREEN_HEIGHT + asteroid.radius * 2:
                    score += 15  # Points for successfully dodging an asteroid
                    if asteroid in asteroids:
                        asteroids.remove(asteroid)

        # Update Particles & Shockwaves
        for particle in particles[:]:
            particle.update()
            if particle.life <= 0:
                particles.remove(particle)

        for sw in shockwaves[:]:
            sw.update()
            if sw.radius >= sw.max_radius:
                shockwaves.remove(sw)

        # Announce score milestones via TTS (10,000, 20,000, ...)
        announcer.check(score)
        health_milestone = apply_health_milestones(player, score, health_milestone)

        # --- Rendering ---
        screen.fill(COLOR_BG)

        # Stars background
        for star in stars:
            star.draw(screen)

        # Shockwaves blast ring
        for sw in shockwaves:
            sw.draw(screen)

        # Particles
        for particle in particles:
            particle.draw(screen)

        # Lasers
        for laser in lasers:
            laser.draw(screen)

        # Asteroids
        for asteroid in asteroids:
            asteroid.draw(screen)

        # Player
        if not game_over:
            player.draw(screen, particles)

        # --- HUD Elements ---
        # Top Bar Background
        hud_rect = pygame.Rect(15, 15, SCREEN_WIDTH - 30, 50)
        pygame.draw.rect(screen, (15, 20, 35), hud_rect, border_radius=8)
        pygame.draw.rect(screen, (50, 70, 100), hud_rect, width=2, border_radius=8)

        # Health Bar
        health_ratio = player.health / player.max_health
        health_bar_rect = pygame.Rect(30, 30, 200 * health_ratio, 20)
        health_bg_rect = pygame.Rect(30, 30, 200, 20)
        pygame.draw.rect(screen, (60, 20, 20), health_bg_rect, border_radius=4)
        pygame.draw.rect(screen, COLOR_GREEN if health_ratio > 0.4 else COLOR_RED, health_bar_rect, border_radius=4)
        pygame.draw.rect(screen, COLOR_WHITE, health_bg_rect, width=1, border_radius=4)

        # Score Display
        score_txt = font_medium.render(f"SCORE: {score:05d}", True, COLOR_YELLOW)
        screen.blit(score_txt, (SCREEN_WIDTH - 220, 26))

        # Control Mode Indicator
        mode_text = "UDP: YOLO POSE CONTROL" if is_udp else "MODE: KEYBOARD ARROWS"
        mode_color = COLOR_CYAN if is_udp else (180, 190, 210)
        mode_sf = font_small.render(mode_text, True, mode_color)
        screen.blit(mode_sf, (SCREEN_WIDTH // 2 - mode_sf.get_width() // 2, 28))

        # Game Over Screen Overlay
        if game_over:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((10, 10, 20, 210))
            screen.blit(overlay, (0, 0))

            title_sf = font_large.render("GAME OVER", True, COLOR_RED)
            score_final_sf = font_medium.render(f"FINAL SCORE: {score}", True, COLOR_WHITE)
            if game_over_started_at is None:
                restart_text = "Press 'R' key or JUMP to Restart"
            else:
                wait_left = max(0, 5.0 - (time.time() - game_over_started_at))
                restart_text = f"Restart available in {wait_left:.1f}s"
            restart_sf = font_small.render(restart_text, True, COLOR_CYAN)

            screen.blit(title_sf, (SCREEN_WIDTH // 2 - title_sf.get_width() // 2, SCREEN_HEIGHT // 2 - 60))
            screen.blit(score_final_sf, (SCREEN_WIDTH // 2 - score_final_sf.get_width() // 2, SCREEN_HEIGHT // 2 + 10))
            screen.blit(restart_sf, (SCREEN_WIDTH // 2 - restart_sf.get_width() // 2, SCREEN_HEIGHT // 2 + 60))

        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
