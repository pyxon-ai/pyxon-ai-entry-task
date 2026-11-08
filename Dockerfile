FROM python:3.11-slim

# LibreOffice is only needed for legacy .doc files
RUN apt-get update && apt-get install -y --no-install-recommends libreoffice-writer fonts-dejavu \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

ENV PYXON_DATA_DIR=/tmp/pyxon-data \
    GRADIO_SERVER_NAME=0.0.0.0 \
    PORT=7860
EXPOSE 7860
CMD ["python", "app.py"]
