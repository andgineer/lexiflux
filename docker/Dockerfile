# Node.js build stage
FROM node:alpine AS node-builder

WORKDIR /lexiflux

COPY *.js* /lexiflux/
COPY lexiflux/viewport /lexiflux/lexiflux/viewport
RUN npm install && npm run build

# ====================
FROM python:3.12

ENV LEXIFLUX_UI_SETTINGS_ONLY=true
ENV LEXIFLUX_SKIP_AUTH=true
ENV OLLAMA_LOAD_MODEL=false

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SECRET_KEY=defaultsecretkey
ENV DJANGO_DEBUG=False
ENV DJANGO_ALLOWED_HOSTS=*

# Install git
RUN apt-get update && apt-get install -y git

WORKDIR /lexiflux

COPY lexiflux ./lexiflux
COPY requirements.txt .
COPY manage .

COPY --from=node-builder /lexiflux/lexiflux/static/lexiflux/bundle.js /lexiflux/lexiflux/static/lexiflux/bundle.js

RUN curl -L https://ollama.ai/install.sh | sh

RUN pip install --no-cache-dir -r requirements.txt gunicorn
RUN ./manage migrate
RUN ./manage default-user

COPY docker/start.sh /start.sh
COPY docker/start_ollama.sh /start_ollama.sh

CMD ["/start.sh"]
