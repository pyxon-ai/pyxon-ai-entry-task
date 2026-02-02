# Deploy AI Parser to Hugging Face Spaces

## Quick Start

### 1. Create Hugging Face Space

1. Go to [huggingface.co/spaces](https://huggingface.co/spaces)
2. Click "Create new Space"
3. Fill in:
   - **Space name:** `ai-parser-dashboard`
   - **License:** Apache 2.0
   - **SDK:** Gradio
   - **Visibility:** Public or Private

### 2. Push Your Code

```bash
# Clone the space
git clone https://huggingface.co/spaces/YOUR_USERNAME/ai-parser-dashboard
cd ai-parser-dashboard

# Copy files
cp /path/to/ai-parser/app.py .
cp /path/to/ai-parser/requirements.txt .
cp /path/to/ai-parser/README.md .

# Commit and push
git add .
git commit -m "Initial commit"
git push
```

### 3. Configure Backend URL

Edit `app.py` and change:
```python
API_BASE_URL = "https://your-fastapi-backend.com"
```

Replace with your deployed FastAPI backend URL.

### 4. Deploy

Hugging Face will automatically:
- Detect `app.py`
- Install `requirements.txt`
- Launch Gradio app on port 7860

Your Space will be live at:
```
https://huggingface.co/spaces/YOUR_USERNAME/ai-parser-dashboard
```

---

## Local Testing

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Start FastAPI Backend

```bash
cd src
uvicorn main:app --reload
```

### 3. Run Gradio App

```bash
python app.py
```

Open: `http://localhost:7860`

---

## Backend Deployment Options

You need to deploy your FastAPI backend first:

### Option 1: Hugging Face Spaces (FastAPI)
- Create another Space with SDK: Docker
- Deploy your FastAPI app
- Use the Space URL as `API_BASE_URL`

### Option 2: Railway
```bash
railway login
railway init
railway up
```

### Option 3: Render
- Connect GitHub repo
- Create Web Service
- Set root as `src/`
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`

### Option 4: Fly.io
```bash
fly launch
fly deploy
```

---

## Environment Variables

If deploying backend on HF Spaces, create `.env`:

```bash
GEMINI_API_KEY=your-key
COHERE_API_KEY=your-key
WEAVIATE_API_KEY=your-key
WEAVIATE_URL=your-cluster.weaviate.cloud
SUPABASE_API_KEY=your-key
SUPABASE_URL=your-url
DATABASE_URL=your-connection-string
```

Add in Space Settings → Repository secrets

---

## Tabs Overview

1. **Upload Documents** - Upload PDF, DOCX, TXT files
2. **Semantic Search** - Vector search with reranking
3. **SQL Search** - Filter with multiple criteria
4. **Run Evaluation** - Test system with 15 questions
5. **Results** - View evaluation scores
6. **Documents** - List all uploaded files

---

## Troubleshooting

### Connection Error
- Check `API_BASE_URL` is correct
- Verify backend is running
- Check CORS settings in FastAPI

### No Results
- Upload documents first
- Run evaluation after uploading test files
- Check backend logs

### Slow Performance
- Reduce search limit
- Use SQL search for simple queries
- Check backend server resources

---

## Support

For issues:
1. Check Gradio app logs
2. Check FastAPI backend logs
3. Verify all API keys are set

Happy deploying! 🚀
