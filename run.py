#!/usr/bin/env python3
"""Eyes Up - Single-command runner for offline bird-call companion."""
import os
import socket
import sys
import uvicorn
from app.config import settings


def get_local_ip() -> str:
    """Detect LAN/Wi-Fi IP for convenient phone connection."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Connecting to a public address (doesn't send data) to discover local interface
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


def main():
    local_ip = get_local_ip()
    print("=" * 60)
    print("🌿 Eyes Up: Offline Bird-Call Companion (Touch Grass Edition)")
    print("=" * 60)
    print(f"Local machine URL : http://localhost:{settings.port}")
    print(f"Phone / Hotspot URL: http://{local_ip}:{settings.port}")
    print(f"Ollama Target     : {settings.ollama_host} (model: {settings.ollama_model})")
    print(f"BirdNET Threshold : {settings.birdnet_confidence_threshold * 100:.0f}%")
    print("=" * 60)
    print("Put your phone in your pocket, listen to the trees, and touch grass!")
    print("=" * 60)

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()
