#!/bin/bash
# Kill all running src.bot processes
ps aux | grep '[p]ython3 -m src.bot' | awk '{print $2}' | xargs -r kill -9

# Запуск тестов
echo "Running tests..."
PYTHONPATH=./ pytest
if [ $? -ne 0 ]; then
  echo "Tests failed! Bot will not start."
  exit 1
fi

# Start new bot instance
python3 -m src.bot 