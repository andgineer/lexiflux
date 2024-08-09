# Node.js build stage
FROM node:alpine AS node-builder

WORKDIR /app

COPY *.js* /app/
COPY lexiflux/viewport /app/lexiflux/viewport
RUN npm install && npm run build

FROM python:3.12

ENV LEXIFLUX_UI_SETTINGS_ONLY=true
ENV LEXIFLUX_SKIP_AUTH=true
ENV OLLAMA_LOAD_MODEL=llama3

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SECRET_KEY=defaultsecretkey
ENV DJANGO_DEBUG=False
ENV DJANGO_ALLOWED_HOSTS=*

COPY lexiflux /lexiflux
COPY --from=node-builder /app/lexiflux/static/lexiflux/bundle.js /lexiflux/static/lexiflux/bundle.js

RUN curl -L https://ollama.ai/install.sh | sh

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

COPY manage /
RUN chmod +x /manage

RUN ./manage migrate
RUN ./manage default-user

COPY docker/start.sh /start.sh
COPY docker/start_ollama.sh /start_ollama.sh

CMD ["/start.sh"]
