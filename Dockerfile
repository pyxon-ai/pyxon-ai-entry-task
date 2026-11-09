FROM python:3.11-slim

# LibreOffice reads legacy .doc files; Tesseract (with Arabic data) reads scanned PDFs
RUN apt-get update && apt-get install -y --no-install-recommends libreoffice-writer fonts-dejavu \
       tesseract-ocr tesseract-ocr-ara tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

# single-threaded Tesseract: the free instance has a fraction of one CPU
ENV OMP_THREAD_LIMIT=1

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

ENV PYXON_DATA_DIR=/tmp/pyxon-data \
    GRADIO_SERVER_NAME=0.0.0.0 \
    PORT=7860
EXPOSE 7860
CMD ["python", "app.py"]
