FROM python:3.13-slim

ARG PIP_DISABLE_PIP_VERSION_CHECK=1
ARG PIP_NO_CACHE_DIR=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /code

# Install dependencies
COPY ./requirements.txt .
RUN pip3 install -r requirements.txt

# Copy application
COPY ./src/whisper_bot ./whisper_bot
COPY ./healthcheck.py .
COPY ./entrypoint.sh .

RUN chmod +x /code/entrypoint.sh

# Healthcheck: verify bot process is alive
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python healthcheck.py || exit 1

ENTRYPOINT ["/code/entrypoint.sh"]
