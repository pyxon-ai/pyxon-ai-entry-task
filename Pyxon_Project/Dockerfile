# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Download necessary NLTK models globally so the chunker won't fail
RUN python -c "import nltk; nltk.download('punkt', download_dir='/usr/local/share/nltk_data'); nltk.download('punkt_tab', download_dir='/usr/local/share/nltk_data')"
ENV NLTK_DATA=/usr/local/share/nltk_data

# Copy the rest of the application code
COPY . .

# Hugging Face Spaces requires the app to listen on port 7860
EXPOSE 7860

# Run app.py when the container launches
CMD ["python", "app.py"]
