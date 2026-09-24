#!/bin/bash
echo "Starting Lexiflux application..."
#exec gunicorn --bind 0.0.0.0:8000 lexiflux.wsgi:application
./manage runserver 0.0.0.0:8000
