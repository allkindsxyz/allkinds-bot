#!/bin/bash
# Kill all running src.bot processes
ps aux | grep '[p]ython3 -m src.bot' | awk '{print $2}' | xargs -r kill -9
# Start new bot instance
python3 -m src.bot 