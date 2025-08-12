#!/bin/sh

while true; do
    python relayDrone.py
    echo "Flask exited. Restarting in 2 seconds..."
    sleep 0.0001
done
