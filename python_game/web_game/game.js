/**
 * SpaceShip Dodge: Web Browser Edition
 * HTML5 Canvas 2D Engine with Web Audio API Synthesizer & WebSocket Pose Tracking.
 */

const canvas = document.getElementById('gameCanvas');
const ctx = canvas.getContext('2d');

const healthFill = document.getElementById('health-fill');
const scoreDisplay = document.getElementById('score-display');
const modeBadge = document.getElementById('mode-badge');
const gameOverScreen = document.getElementById('game-over-screen');
const finalScoreText = document.getElementById('final-score');
const restartBtn = document.getElementById('restart-btn');

const WIDTH = 1000;
const HEIGHT = 750;

// --- Web Audio API Synthesizer ---
class WebAudioSynth {
    constructor() {
        this.ctx = null;
    }

    init() {
        if (!this.ctx) {
            const AudioCtx = window.AudioContext || window.webkitAudioContext;
            if (AudioCtx) this.ctx = new AudioCtx();
        }
        if (this.ctx && this.ctx.state === 'suspended') {
            this.ctx.resume();
        }
    }

    playLaser() {
        if (!this.ctx) return;
        const now = this.ctx.currentTime;
        const osc = this.ctx.createOscillator();
        const gain = this.ctx.createGain();

        osc.type = 'sawtooth';
        osc.frequency.setValueAtTime(950, now);
        osc.frequency.exponentialRampToValueAtTime(200, now + 0.12);

        gain.gain.setValueAtTime(0.2, now);
        gain.gain.exponentialRampToValueAtTime(0.01, now + 0.12);

        osc.connect(gain);
        gain.connect(this.ctx.destination);

        osc.start(now);
        osc.stop(now + 0.12);
    }

    playExplosion() {
        if (!this.ctx) return;
        const now = this.ctx.currentTime;
        const bufferSize = this.ctx.sampleRate * 0.3;
        const buffer = this.ctx.createBuffer(1, bufferSize, this.ctx.sampleRate);
        const data = buffer.getChannelData(0);
        for (let i = 0; i < bufferSize; i++) {
            data[i] = Math.random() * 2 - 1;
        }

        const noise = this.ctx.createBufferSource();
        noise.buffer = buffer;

        const filter = this.ctx.createBiquadFilter();
        filter.type = 'lowpass';
        filter.frequency.setValueAtTime(800, now);
        filter.frequency.exponentialRampToValueAtTime(80, now + 0.3);

        const gain = this.ctx.createGain();
        gain.gain.setValueAtTime(0.35, now);
        gain.gain.exponentialRampToValueAtTime(0.01, now + 0.3);

        noise.connect(filter);
        filter.connect(gain);
        gain.connect(this.ctx.destination);

        noise.start(now);
    }

    playHit() {
        if (!this.ctx) return;
        const now = this.ctx.currentTime;
        const osc = this.ctx.createOscillator();
        const gain = this.ctx.createGain();

        osc.type = 'sine';
        osc.frequency.setValueAtTime(1200, now);
        osc.frequency.exponentialRampToValueAtTime(400, now + 0.08);

        gain.gain.setValueAtTime(0.15, now);
        gain.gain.exponentialRampToValueAtTime(0.01, now + 0.08);

        osc.connect(gain);
        gain.connect(this.ctx.destination);

        osc.start(now);
        osc.stop(now + 0.08);
    }

    playDamage() {
        if (!this.ctx) return;
        const now = this.ctx.currentTime;
        const osc = this.ctx.createOscillator();
        const gain = this.ctx.createGain();

        osc.type = 'square';
        osc.frequency.setValueAtTime(110, now);
        osc.frequency.exponentialRampToValueAtTime(60, now + 0.25);

        gain.gain.setValueAtTime(0.3, now);
        gain.gain.exponentialRampToValueAtTime(0.01, now + 0.25);

        osc.connect(gain);
        gain.connect(this.ctx.destination);

        osc.start(now);
        osc.stop(now + 0.25);
    }

    playBomb() {
        if (!this.ctx) return;
        const now = this.ctx.currentTime;
        const osc = this.ctx.createOscillator();
        const gain = this.ctx.createGain();

        osc.type = 'sawtooth';
        osc.frequency.setValueAtTime(160, now);
        osc.frequency.exponentialRampToValueAtTime(30, now + 0.5);

        gain.gain.setValueAtTime(0.5, now);
        gain.gain.exponentialRampToValueAtTime(0.01, now + 0.5);

        osc.connect(gain);
        gain.connect(this.ctx.destination);

        osc.start(now);
        osc.stop(now + 0.5);
    }
}

const audio = new WebAudioSynth();

// --- Sound unlock -----------------------------------------------------------
// Browsers block AudioContext & SpeechSynthesis until the page receives a user
// gesture. Pose-driven players never click the page, so we show a one-time
// "tap to enable sound" prompt and unlock on the first tap/click/keypress.
const soundStart = document.getElementById('sound-start');
const soundStartBtn = document.getElementById('sound-start-btn');
let audioUnlocked = false;

function enableAudio() {
    if (audioUnlocked) return;
    audioUnlocked = true;
    audio.init();
    try {
        if ('speechSynthesis' in window) window.speechSynthesis.cancel();
    } catch (e) {}
    if (soundStart) soundStart.classList.remove('active');
}

if (soundStartBtn) {
    soundStartBtn.addEventListener('pointerdown', enableAudio);
    soundStartBtn.addEventListener('touchend', enableAudio, { passive: true });
}
// Fallback: any interaction anywhere on the page unlocks sound.
['pointerdown', 'touchstart', 'keydown'].forEach(evt =>
    window.addEventListener(evt, enableAudio, { once: true, capture: true })
);
// ---------------------------------------------------------------------------

// --- WebSocket Pose Receiver ---
let poseState = { x: 0.5, y: 0.8, shoot: false, bomb: false, active: false };

function initWebSocket() {
    const host = window.location.hostname || 'localhost';
    const wsUrl = `ws://${host}:8080`;
    console.log(`Connecting to Pose WebSocket Bridge -> ${wsUrl}`);

    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
        console.log("WebSocket connected!");
    };

    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            poseState.x = data.x ?? poseState.x;
            poseState.y = data.y ?? poseState.y;
            poseState.shoot = data.shoot ?? false;
            poseState.jump = data.jump ?? false;
            poseState.restart = data.restart ?? false;
            poseState.bomb = data.bomb ?? false;
            poseState.active = true;
            modeBadge.innerText = "CONTROL: YOLO POSE 🦘";
            modeBadge.style.color = "#00ff80";
        } catch (e) {}
    };

    ws.onclose = () => {
        poseState.active = false;
        setTimeout(initWebSocket, 3000);
    };

    ws.onerror = () => {
        ws.close();
    };
}

initWebSocket();

// --- Game Objects ---

class Star {
    constructor() {
        this.reset(true);
    }

    reset(randomY = false) {
        this.x = Math.random() * WIDTH;
        this.y = randomY ? Math.random() * HEIGHT : -10;
        this.size = Math.random() * 2.2 + 0.8;
        this.speed = this.size * 1.5;
        this.brightness = Math.floor(Math.random() * 155 + 100);
    }

    update() {
        this.y += this.speed;
        if (this.y > HEIGHT) this.reset();
    }

    draw() {
        ctx.fillStyle = `rgb(${this.brightness}, ${this.brightness}, ${Math.min(255, this.brightness * 1.1)})`;
        ctx.beginPath();
        ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
        ctx.fill();
    }
}

class Particle {
    constructor(x, y, color) {
        this.x = x;
        this.y = y;
        this.vx = (Math.random() - 0.5) * 8;
        this.vy = (Math.random() - 0.5) * 8;
        this.radius = Math.random() * 4 + 2;
        this.color = color;
        this.life = 1.0;
        this.decay = Math.random() * 0.03 + 0.02;
    }

    update() {
        this.x += this.vx;
        this.y += this.vy;
        this.life -= this.decay;
    }

    draw() {
        if (this.life > 0) {
            ctx.save();
            ctx.globalAlpha = Math.max(0, this.life);
            ctx.fillStyle = this.color;
            ctx.beginPath();
            ctx.arc(this.x, this.y, Math.max(1, this.radius * this.life), 0, Math.PI * 2);
            ctx.fill();
            ctx.restore();
        }
    }
}

class Laser {
    constructor(x, y) {
        this.x = x;
        this.y = y;
        this.speed = 14;
    }

    update() {
        this.y -= this.speed;
    }

    draw() {
        ctx.strokeStyle = '#00f0ff';
        ctx.lineWidth = 4;
        ctx.beginPath();
        ctx.moveTo(this.x, this.y);
        ctx.lineTo(this.x, this.y + 16);
        ctx.stroke();
    }
}

class Shockwave {
    constructor(x, y) {
        this.x = x;
        this.y = y;
        this.radius = 10;
        this.maxRadius = 900;
        this.speed = 35;
    }

    update() {
        this.radius += this.speed;
    }

    draw() {
        if (this.radius < this.maxRadius) {
            const alpha = Math.max(0, 1.0 - this.radius / this.maxRadius);
            const width = Math.max(2, Math.floor(16 * alpha));

            ctx.save();
            ctx.globalAlpha = alpha;
            ctx.strokeStyle = '#ff00b4';
            ctx.lineWidth = width;
            ctx.beginPath();
            ctx.arc(this.x, this.y, this.radius, 0, Math.PI * 2);
            ctx.stroke();

            ctx.strokeStyle = '#00f0ff';
            ctx.lineWidth = Math.max(1, width / 2);
            ctx.beginPath();
            ctx.arc(this.x, this.y, this.radius * 0.85, 0, Math.PI * 2);
            ctx.stroke();
            ctx.restore();
        }
    }
}

class Obstacle {
    constructor(difficulty = 1.0) {
        this.radius = Math.floor(Math.random() * 26 + 22);
        this.x = Math.random() * (WIDTH - this.radius * 2) + this.radius;
        this.y = -this.radius * 2;
        // Slow and smooth falling speed for comfortable reaction time
        const baseSpeed = Math.random() * 1.2 + 1.2;
        const speedMult = 1.0 + Math.min(0.8, (difficulty - 1.0) * 0.08);
        this.speed = baseSpeed * speedMult;
        this.rotation = Math.random() * Math.PI * 2;
        this.rotSpeed = (Math.random() - 0.5) * 0.06;
        this.hp = Math.max(1, Math.floor(this.radius / 16));

        const types = ["crystal", "ufo", "fireball", "space_rock"];
        this.kind = types[Math.floor(Math.random() * types.length)];
        const colors = ["#ff00b4", "#00f0ff", "#00ff80", "#ffd700", "#ff5000", "#b45aff"];
        this.color = colors[Math.floor(Math.random() * colors.length)];
    }

    update(particles) {
        this.y += this.speed;
        this.rotation += this.rotSpeed;

        if (particles && Math.random() < 0.5) {
            if (this.kind === "fireball") {
                particles.push(new Particle(this.x + (Math.random() - 0.5) * 12, this.y - 10, '#ff6400'));
            } else if (this.kind === "crystal") {
                particles.push(new Particle(this.x + (Math.random() - 0.5) * 16, this.y + (Math.random() - 0.5) * 16, this.color));
            }
        }
    }

    draw() {
        ctx.save();
        ctx.translate(this.x, this.y);

        if (this.kind === "crystal") {
            ctx.fillStyle = this.color;
            ctx.strokeStyle = '#ffffff';
            ctx.lineWidth = 2;
            ctx.beginPath();
            const r = this.radius;
            ctx.moveTo(0, -r);
            ctx.lineTo(r * 0.7, -r * 0.2);
            ctx.lineTo(r * 0.6, r * 0.7);
            ctx.lineTo(0, r);
            ctx.lineTo(-r * 0.6, r * 0.7);
            ctx.lineTo(-r * 0.7, -r * 0.2);
            ctx.closePath();
            ctx.fill();
            ctx.stroke();
        } else if (this.kind === "ufo") {
            const r = this.radius;
            ctx.fillStyle = '#283c5a';
            ctx.strokeStyle = this.color;
            ctx.lineWidth = 3;
            ctx.beginPath();
            ctx.ellipse(0, 0, r, r * 0.4, 0, 0, Math.PI * 2);
            ctx.fill();
            ctx.stroke();

            ctx.fillStyle = '#00f0ff';
            ctx.beginPath();
            ctx.ellipse(0, -r * 0.3, r * 0.5, r * 0.4, 0, 0, Math.PI * 2);
            ctx.fill();
        } else if (this.kind === "fireball") {
            const r = this.radius;
            ctx.fillStyle = '#ff6400';
            ctx.beginPath();
            ctx.arc(0, 0, r, 0, Math.PI * 2);
            ctx.fill();

            ctx.fillStyle = '#ffe632';
            ctx.beginPath();
            ctx.arc(0, 0, r * 0.6, 0, Math.PI * 2);
            ctx.fill();
        } else {
            const r = this.radius;
            ctx.fillStyle = '#1e2438';
            ctx.strokeStyle = this.color;
            ctx.lineWidth = 3;
            ctx.beginPath();
            ctx.arc(0, 0, r, 0, Math.PI * 2);
            ctx.fill();
            ctx.stroke();
        }

        ctx.restore();
    }
}

const PLAYER_Y = HEIGHT * 0.88;

class Player {
    constructor() {
        this.x = WIDTH / 2;
        this.y = PLAYER_Y;
        this.targetX = this.x;
        this.radius = 24;
        this.health = 100;
        this.shootCooldown = 0;
    }

    update(normX, normY, isPose) {
        if (isPose) {
            this.targetX = normX * WIDTH;
        }

        this.x += (this.targetX - this.x) * 0.18;
        this.x = Math.max(30, Math.min(WIDTH - 30, this.x));
        this.y = PLAYER_Y;

        if (this.shootCooldown > 0) this.shootCooldown--;
    }

    draw() {
        ctx.save();
        ctx.translate(this.x, this.y);

        // Ship body
        ctx.fillStyle = '#00f0ff';
        ctx.strokeStyle = '#ff0080';
        ctx.lineWidth = 3;

        ctx.beginPath();
        ctx.moveTo(0, -26);
        ctx.lineTo(-24, 22);
        ctx.lineTo(-10, 14);
        ctx.lineTo(10, 14);
        ctx.lineTo(24, 22);
        ctx.closePath();
        ctx.fill();
        ctx.stroke();

        ctx.restore();
    }
}

// --- Main Game State ---

const stars = Array.from({ length: 90 }, () => new Star());
const particles = [];
const lasers = [];
const obstacles = [];
const shockwaves = [];

let player = new Player();
let score = 0;
let gameOver = false;
let spawnTimer = 0;
let bombCooldown = 0;
let lastMilestone = 0;

// Inputs
const keys = {};
window.addEventListener('keydown', (e) => {
    enableAudio();
    keys[e.code] = true;
    if (e.code === 'KeyR' && gameOver) resetGame();
});
window.addEventListener('keyup', (e) => keys[e.code] = false);

// Mouse control fallback (Horizontal Only)
canvas.addEventListener('mousemove', (e) => {
    if (!poseState.active && !gameOver) {
        const rect = canvas.getBoundingClientRect();
        player.targetX = (e.clientX - rect.left) * (WIDTH / rect.width);
    }
});
canvas.addEventListener('mousedown', () => {
    enableAudio();
    if (!gameOver && player.shootCooldown === 0) {
        shootLasers();
    }
});

function shootLasers() {
    lasers.push(new Laser(player.x - 14, player.y - 10));
    lasers.push(new Laser(player.x + 14, player.y - 10));
    player.shootCooldown = 12;
    audio.playLaser();
}

// Speak score milestones (10,000, 20,000, ...) via the built-in Speech Synthesis API.
function announceScore(score) {
    if (!('speechSynthesis' in window)) return;
    const msg = new SpeechSynthesisUtterance(String(score));
    msg.rate = 1.1;
    msg.pitch = 1.3;
    if (window.speechSynthesis.speaking) window.speechSynthesis.cancel();
    window.speechSynthesis.speak(msg);
}

function triggerBomb() {
    if (bombCooldown === 0 && !gameOver) {
        bombCooldown = 90;
        shockwaves.push(new Shockwave(player.x, player.y));
        audio.playBomb();

        for (let i = obstacles.length - 1; i >= 0; i--) {
            const obs = obstacles[i];
            score += Math.floor(obs.radius * 3) + 30;
            for (let p = 0; p < 20; p++) {
                particles.push(new Particle(obs.x, obs.y, '#ff00b4'));
            }
            obstacles.splice(i, 1);
        }
    }
}

let gameOverFrames = 0;

function resetGame() {
    player = new Player();
    obstacles.length = 0;
    lasers.length = 0;
    particles.length = 0;
    shockwaves.length = 0;
    score = 0;
    bombCooldown = 0;
    lastMilestone = 0;
    gameOver = false;
    gameOverFrames = 0;
    gameOverScreen.classList.remove('active');
}

restartBtn.addEventListener('click', resetGame);

// --- Game Loop ---

function gameLoop() {
    spawnTimer++;

    // Clear Background
    ctx.fillStyle = '#0a0c18';
    ctx.fillRect(0, 0, WIDTH, HEIGHT);

    // Stars
    stars.forEach(s => { s.update(); s.draw(); });

    if (gameOver) {
        gameOverFrames++;
        if (gameOverFrames > 8 && poseState.active && (poseState.jump || poseState.restart || poseState.shoot || poseState.bomb)) {
            resetGame();
        }
    } else {
        // Survival score
        if (spawnTimer % 6 === 0) score++;

        // Announce 10,000-point milestones via TTS
        const milestone = Math.floor(score / 10000);
        if (milestone > lastMilestone && milestone >= 1) {
            lastMilestone = milestone;
            announceScore(milestone * 10000);
        }

        // Keyboard controls (Horizontal Only)
        if (!poseState.active) {
            const speed = 9;
            if (keys['ArrowLeft'] || keys['KeyA']) player.targetX -= speed;
            if (keys['ArrowRight'] || keys['KeyD']) player.targetX += speed;
        }

        // Shoot trigger
        if ((keys['Space'] || (poseState.active && poseState.shoot)) && player.shootCooldown === 0) {
            shootLasers();
        }

        // Super Bomb Trigger (Key 'B' / Shift OR Pose Double Jump / Both Hands Up)
        if ((keys['KeyB'] || keys['ShiftLeft'] || keys['ShiftRight'] || (poseState.active && poseState.bomb))) {
            triggerBomb();
        }

        if (bombCooldown > 0) bombCooldown--;

        // Update player
        player.update(poseState.x, poseState.y, poseState.active);

        // Spawn obstacles
        const difficulty = 1.0 + (score / 700);
        const spawnInterval = Math.max(32, Math.floor(65 / difficulty));
        if (spawnTimer >= spawnInterval) {
            obstacles.push(new Obstacle(difficulty));
            spawnTimer = 0;
        }

        // Update lasers
        for (let i = lasers.length - 1; i >= 0; i--) {
            lasers[i].update();
            lasers[i].draw();
            if (lasers[i].y < -30) lasers.splice(i, 1);
        }

        // Update obstacles & collisions
        for (let i = obstacles.length - 1; i >= 0; i--) {
            const obs = obstacles[i];
            obs.update(particles);
            obs.draw();

            // Laser hit check
            for (let j = lasers.length - 1; j >= 0; j--) {
                const l = lasers[j];
                const dist = Math.hypot(l.x - obs.x, l.y - obs.y);
                if (dist < obs.radius + 6) {
                    lasers.splice(j, 1);
                    obs.hp--;
                    audio.playHit();

                    for (let p = 0; p < 6; p++) particles.push(new Particle(l.x, l.y, '#ffd700'));

                    if (obs.hp <= 0) {
                        score += Math.floor(obs.radius * 3) + 20;
                        audio.playExplosion();
                        for (let p = 0; p < 18; p++) particles.push(new Particle(obs.x, obs.y, '#00f0ff'));
                        obstacles.splice(i, 1);
                        break;
                    }
                }
            }

            // Player collision check
            const distP = Math.hypot(player.x - obs.x, player.y - obs.y);
            if (distP < player.radius + obs.radius * 0.8) {
                player.health -= 25;
                audio.playDamage();
                for (let p = 0; p < 25; p++) particles.push(new Particle(player.x, player.y, '#ff3c3c'));
                obstacles.splice(i, 1);

                if (player.health <= 0) {
                    player.health = 0;
                    gameOver = true;
                    gameOverScreen.classList.add('active');
                    finalScoreText.innerText = `FINAL SCORE: ${score}`;
                }
            } else if (obs.y > HEIGHT + obs.radius * 2) {
                score += 15; // Dodge bonus
                obstacles.splice(i, 1);
            }
        }

        player.draw();
    }

    // Update Particles & Shockwaves
    for (let i = particles.length - 1; i >= 0; i--) {
        particles[i].update();
        particles[i].draw();
        if (particles[i].life <= 0) particles.splice(i, 1);
    }

    for (let i = shockwaves.length - 1; i >= 0; i--) {
        shockwaves[i].update();
        shockwaves[i].draw();
        if (shockwaves[i].radius >= shockwaves[i].maxRadius) shockwaves.splice(i, 1);
    }

    // Update UI HUD
    healthFill.style.width = `${Math.max(0, player.health)}%`;
    scoreDisplay.innerText = `SCORE: ${String(score).padStart(5, '0')}`;

    requestAnimationFrame(gameLoop);
}

requestAnimationFrame(gameLoop);
