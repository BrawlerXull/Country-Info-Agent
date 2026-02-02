#!/bin/bash
export PYTHONPATH=$PYTHONPATH:.
# Check if venv exists, if so activate it
if [ -d "venv" ]; then
    source venv/bin/activate
fi
uvicorn app.api:app --host 0.0.0.0 --port 8000
