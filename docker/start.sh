#!/bin/bash
set -e
echo "Starting Lexiflux application..."
# Saved AI keys are encrypted with this secret, so it stays in the container with the database.
if [ -z "$DJANGO_SECRET_KEY" ] && [ ! -s .secret_key ]; then
    (umask 077 && python -c "import secrets; print(secrets.token_urlsafe(50))" > .secret_key)
fi
./manage migrate --noinput
#exec gunicorn --bind 0.0.0.0:8000 lexiflux.wsgi:application
./manage runserver 0.0.0.0:8000
