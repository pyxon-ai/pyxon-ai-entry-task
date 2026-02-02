# AI Parser - Streamlit Dashboard Deployment Guide

## 🚀 Deploy to Streamlit Cloud

### Prerequisites
1. GitHub account
2. Streamlit Cloud account (free at [streamlit.io](https://streamlit.io))
3. Your FastAPI backend deployed and accessible

### Step 1: Prepare Your Repository

1. **Ensure these files exist:**
   - `streamlit_app.py` ✅
   - `requirements_streamlit.txt` ✅
   - `.streamlit/config.toml` ✅

2. **Push to GitHub:**
   ```bash
   git add streamlit_app.py requirements_streamlit.txt .streamlit/
   git commit -m "Add Streamlit dashboard"
   git push origin main
   ```

### Step 2: Deploy on Streamlit Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Click "New app"
3. Connect your GitHub repository
4. Select:
   - **Repository:** `EyadAlN3imi/pyxon-ai-entry-task`
   - **Branch:** `main`
   - **Main file path:** `streamlit_app.py`
5. Click "Deploy"

### Step 3: Configure Secrets

In Streamlit Cloud settings, add your secrets:

```toml
API_BASE_URL = "https://your-fastapi-backend.com"
```

Replace with your actual FastAPI backend URL.

### Step 4: Test the Dashboard

1. Wait for deployment to complete
2. Your app will be live at: `https://your-app-name.streamlit.app`
3. Click "Run Evaluation" to test
4. View results and statistics

---

## 🖥️ Run Locally

### Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements_streamlit.txt
   ```

2. **Configure secrets:**
   
   Edit `.streamlit/secrets.toml`:
   ```toml
   API_BASE_URL = "http://localhost:8000"
   ```

3. **Run the app:**
   ```bash
   streamlit run streamlit_app.py
   ```

4. **Open browser:** http://localhost:8501

---

## 📊 Dashboard Features

### Overview Page
- Total questions and pass rate
- Average scores by criteria
- Score distribution charts
- Pass/fail ratio

### Detailed Results
- Filter by source file
- Filter by score range
- View individual question results
- See retrieved chunks and judge reasoning

### Analytics
- Performance by source file
- Score trends across questions
- Export results (JSON/CSV)

### Run Evaluation
- Trigger new evaluation
- View last run timestamp
- Progress indicator

---

## 🔧 API Endpoints Used

The dashboard connects to these FastAPI endpoints:

- `POST /api/v1/evaluate/run` - Run evaluation
- `GET /api/v1/evaluate/results` - Fetch results
- `GET /api/v1/evaluate/statistics` - Get statistics

Make sure your FastAPI backend is running and accessible!

---

## 🎨 Customization

### Change Theme

Edit `.streamlit/config.toml`:

```toml
[theme]
primaryColor = "#FF4B4B"
backgroundColor = "#0E1117"
secondaryBackgroundColor = "#262730"
textColor = "#FAFAFA"
```

### Modify Dashboard

Edit `streamlit_app.py` to:
- Add new visualizations
- Change filters
- Customize layout
- Add more metrics

---

## ⚠️ Troubleshooting

### Connection Error
- Verify `API_BASE_URL` in secrets
- Check FastAPI backend is running
- Ensure CORS is enabled in FastAPI

### Missing Data
- Run evaluation first
- Check `evaluation_results.json` exists
- Verify API responses

### Deployment Issues
- Check all files are committed
- Verify `requirements_streamlit.txt` is complete
- Check Streamlit Cloud logs

---

## 📞 Support

For issues, check:
1. Streamlit logs in Cloud dashboard
2. FastAPI logs in backend
3. Browser console for errors

Happy evaluating! 🎉
