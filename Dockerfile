FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    DJANGO_SETTINGS_MODULE=config.settings.production

WORKDIR /app

RUN groupadd --gid 1000 app \
    && useradd --uid 1000 --gid app --home-dir /app --shell /usr/sbin/nologin --no-create-home app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
RUN chmod 755 docker/entrypoint.sh docker/start.sh \
    && mkdir -p staticfiles media \
    && chown app:app staticfiles media

EXPOSE 8001

ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["daphne", "-b", "0.0.0.0", "-p", "8001", "config.asgi:application"]
