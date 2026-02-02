#!/bin/bash

# Pyxon AI Document Parser - Setup and Run Script

echo "🚀 Pyxon AI Document Parser Setup"
echo "=================================="

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "✅ Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Download NLTK data
echo "📚 Downloading NLTK data..."
python -c "import nltk; nltk.download('punkt', quiet=True)"

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p uploads chroma_db benchmarks/results

# Copy environment file if not exists
if [ ! -f ".env" ]; then
    echo "⚙️  Creating .env file..."
    cp .env.example .env
    echo "⚠️  Please edit .env file with your database credentials"
fi

echo ""
echo "✨ Setup complete!"
echo ""
echo "To start the application:"
echo "  1. Make sure PostgreSQL is running"
echo "  2. Update .env with your database credentials"
echo "  3. Run: uvicorn app.main:app --reload"
echo ""
echo "Or use Docker:"
echo "  docker-compose up -d"
echo ""
echo "Access the application at: http://localhost:8000"
echo "API Documentation: http://localhost:8000/api/docs"
