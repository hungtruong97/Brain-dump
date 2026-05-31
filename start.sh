#!/data/data/com.termux/files/usr/bin/bash
# Run once after boot (or manually) inside Termux.
# Keeps screen on and starts the server so Tasker can reach it.

termux-wake-lock

# Show local IP (works without root in Termux)
echo "Local IP:"
hostname -I | tr ' ' '\n' | grep '192\.'

cd "$(dirname "$0")"

# Termux ships python3; use the module form so PATH doesn't matter
python -m pip install -q -r requirements.txt

python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
