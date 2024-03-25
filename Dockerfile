FROM python:3

# Create working directory under /app
WORKDIR /app
COPY src /app
RUN python3 -m pip install -r /app/requirements.txt

ENTRYPOINT ["python3", "/app/monitor.py"]
