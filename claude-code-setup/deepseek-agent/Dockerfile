FROM python:3.10-slim

LABEL description="DeepSeek Agent — 24/7 scheduled AI tasks"

# APScheduler — single dependency
RUN pip install --no-cache-dir apscheduler==3.10.4

WORKDIR /app

COPY deepseek_api.py .
COPY agent.py .

EXPOSE 8766

HEALTHCHECK --interval=60s --timeout=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8766/health')" || exit 1

CMD ["python", "agent.py"]
