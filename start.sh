#!/data/data/com.termux/files/usr/bin/bash
# Run once after boot (or manually) inside Termux.
# Keeps screen on and starts the server so Tasker can reach it.

termux-wake-lock

# Show local IP using Python (Termux hostname doesn't support -I)
echo "Local IP:"
python -c "import socket; s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); s.connect(('8.8.8.8',80)); print(s.getsockname()[0]); s.close()"

cd "$(dirname "$0")"

# orjson (required by anthropic) ships as a pre-compiled Termux package
pkg install -y python-orjson 2>/dev/null || true

# Termux ships python3; use the module form so PATH doesn't matter
python -m pip cache purge -q 2>/dev/null || true
python -m pip install -q -r requirements.txt

python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
