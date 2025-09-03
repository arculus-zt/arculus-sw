#!/bin/bash

WATCH_FILE="auth_mode.txt"  # The file to watch

echo "Watching $WATCH_FILE for changes..."

# Run the script initially
python3 supplyDrone.py &
PID=$!

while true; do
    # Wait for modifications
    inotifywait -e modify,create,delete "$WATCH_FILE"

    # Kill the running script
    echo "$(date): Change detected. Restarting $WATCH_FILE..."
    kill $PID 2>/dev/null

    # Give a moment for cleanup
    sleep 1

    # Restart the script
    python3 supplyDrone.py &
    PID=$!
done
