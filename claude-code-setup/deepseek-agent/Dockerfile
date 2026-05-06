FROM python:3.10-slim

RUN pip install --no-cache-dir apscheduler==3.10.4 requests

WORKDIR /app

COPY *.py /app/

# Remove healthcheck on startup to avoid restart loop
# HEALTHCHECK set in docker-compose.yml

CMD ["python", "agent.py"]
