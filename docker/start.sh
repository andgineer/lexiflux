#!/bin/bash
# Start Ollama initialization in the background
/start_ollama.sh &

echo "Starting Lexiflux application..."
#exec gunicorn --bind 0.0.0.0:8000 lexiflux.wsgi:application
./manage runserver 0.0.0.0:8000
