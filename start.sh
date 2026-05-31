#!/data/data/com.termux/files/usr/bin/bash
# Run once after boot (or manually) inside Termux.
# Keeps screen on and starts the server so Tasker can reach it.

termux-wake-lock

# Show local IP so you can point Tasker at it
echo "Local IP:"
ip addr show wlan0 | grep 'inet ' | awk '{print $2}' | cut -d/ -f1

cd "$(dirname "$0")"
pip install -q -r requirements.txt

uvicorn main:app --host 0.0.0.0 --port 8000 --reload
