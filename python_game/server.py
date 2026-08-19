#!/usr/bin/env python3
"""
Web Server & Pose WebSocket Bridge
Serves web_game/ static files on http://localhost:8000 and bridges UDP pose telemetry from 
pose_tracker.py (UDP 5005) to WebSockets clients on ws://localhost:8080.
"""

import sys
import os
import socket
import json
import threading
import time
import hashlib
import base64
import struct
from http.server import HTTPServer, SimpleHTTPRequestHandler

HTTP_PORT = 8000
WS_PORT = 8080
UDP_PORT = 5005

# Directory containing web_game static files
WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web_game")

# Global set of connected WebSocket client sockets
ws_clients = set()
ws_clients_lock = threading.Lock()

# Latest pose state
pose_state = {"x": 0.5, "y": 0.8, "shoot": False, "active": False, "time": 0}

# --- Lightweight Zero-Dependency WebSocket Server ---

def build_ws_frame(message_str):
    """Encodes a string into a simple unmasked WebSocket text frame (Opcode 1)."""
    payload = message_str.encode('utf-8')
    length = len(payload)
    if length <= 125:
        header = bytes([0x81, length])
    elif length <= 65535:
        header = bytes([0x81, 126]) + struct.pack("!H", length)
    else:
        header = bytes([0x81, 127]) + struct.pack("!Q", length)
    return header + payload

def handle_ws_client(client_socket, client_address):
    """Handles WebSocket handshake and keeps connection alive."""
    print(f"[WebSocket] New connection from {client_address}")
    try:
        # Read HTTP GET handshake request
        request = client_socket.recv(2048).decode('utf-8', errors='ignore')
        if "Sec-WebSocket-Key" not in request:
            client_socket.close()
            return

        # Extract Sec-WebSocket-Key
        key = ""
        for line in request.split("\r\n"):
            if line.startswith("Sec-WebSocket-Key:"):
                key = line.split(":")[1].strip()
                break

        # Compute Sec-WebSocket-Accept key
        MAGIC_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
        accept_key = base64.b64encode(hashlib.sha1((key + MAGIC_GUID).encode('utf-8')).digest()).decode('utf-8')

        handshake_response = (
            "HTTP/1.1 101 Switching Protocols\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Accept: {accept_key}\r\n\r\n"
        )
        client_socket.sendall(handshake_response.encode('utf-8'))

        with ws_clients_lock:
            ws_clients.add(client_socket)

        # Keep connection open and read ping/pong/close frames
        while True:
            data = client_socket.recv(1024)
            if not data:
                break
    except Exception:
        pass
    finally:
        with ws_clients_lock:
            ws_clients.discard(client_socket)
        try:
            client_socket.close()
        except Exception:
            pass
        print(f"[WebSocket] Client disconnected {client_address}")

def websocket_server_thread():
    """Server loop listening for incoming WebSocket connections on WS_PORT."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", WS_PORT))
    sock.listen(10)
    print(f"[WebSocket Bridge] Server listening on ws://0.0.0.0:{WS_PORT}...")

    while True:
        try:
            client_socket, client_address = sock.accept()
            t = threading.Thread(target=handle_ws_client, args=(client_socket, client_address), daemon=True)
            t.start()
        except Exception as e:
            time.sleep(0.5)

# --- UDP Listener & WebSocket Broadcast Thread ---

def udp_listener_thread():
    """Listens for UDP packets on UDP_PORT and broadcasts them to all WebSocket clients."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    except Exception:
        pass
    try:
        sock.bind(("127.0.0.1", UDP_PORT))
        sock.settimeout(0.5)
        print(f"[UDP Listener] Bridge listening for UDP pose stream on port {UDP_PORT}...")
    except Exception as e:
        print(f"[UDP Error] Could not bind to UDP port {UDP_PORT}: {e}")
        return

    while True:
        try:
            data, _ = sock.recvfrom(1024)
            payload = json.loads(data.decode('utf-8'))
            pose_state.update(payload)
            pose_state["active"] = True

            # Broadcast frame to all connected WebSocket browsers
            msg = json.dumps(pose_state)
            frame = build_ws_frame(msg)

            with ws_clients_lock:
                dead_clients = set()
                for client in list(ws_clients):
                    try:
                        client.sendall(frame)
                    except Exception:
                        dead_clients.add(client)
                ws_clients.difference_update(dead_clients)

        except socket.timeout:
            pass
        except Exception as e:
            pass

# --- Static HTTP File Server ---

class CustomHTTPHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEB_DIR, **kwargs)

    def log_message(self, format, *args):
        # Quiet HTTP access logs
        pass

def http_server_thread():
    """Serves web_game/ static files over HTTP."""
    server_address = ("0.0.0.0", HTTP_PORT)
    httpd = HTTPServer(server_address, CustomHTTPHandler)
    print(f"[HTTP Server] Serving Web Game at http://localhost:{HTTP_PORT}")
    httpd.serve_forever()

def main():
    if not os.path.exists(WEB_DIR):
        print(f"[Error] Web directory not found: {WEB_DIR}")
        sys.exit(1)

    print("\n=======================================================")
    print("  🚀 SPACE SHOOTER WEB SERVER & POSE BRIDGE")
    print(f"  - Web App URL:  http://localhost:{HTTP_PORT}")
    print(f"  - Network URL:  http://0.0.0.0:{HTTP_PORT}")
    print(f"  - WebSocket:    ws://localhost:{WS_PORT}")
    print(f"  - UDP Listener: 127.0.0.1:{UDP_PORT}")
    print("=======================================================\n")

    # Start threads
    t_http = threading.Thread(target=http_server_thread, daemon=True)
    t_ws = threading.Thread(target=websocket_server_thread, daemon=True)
    t_udp = threading.Thread(target=udp_listener_thread, daemon=True)

    t_http.start()
    t_ws.start()
    t_udp.start()

    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        print("\n[Server] Shutting down...")

if __name__ == "__main__":
    main()
