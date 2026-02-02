# 🚂 Deploy AI Parser Dashboard to Railway

## Quick Setup (5 minutes)

### Step 1: Prepare Repository

All files are ready! Just push to GitHub:
```bash
git add railway.json Procfile runtime.txt requirements.txt streamlit_app.py
git commit -m "Setup for Railway deployment"
git push origin main
```

### Step 2: Deploy on Railway

1. **Go to:** [railway.app](https://railway.app)
2. **Sign up** with GitHub (free)
3. Click **"New Project"**
4. Select **"Deploy from GitHub repo"**
5. Choose your repository: `pyxon-ai-entry-task`
6. Railway will auto-detect and deploy! ✅

### Step 3: Configure Environment Variables

In Railway dashboard:

1. Click on your app
2. Go to **"Variables"** tab
3. Add these secrets:

```env
API_BASE_URL=your-fastapi-backend-url

GEMINI_API_KEY=your-gemini-api-key-here
COHERE_API_KEY=your-cohere-api-key-here

WEAVIATE_API_KEY=your-weaviate-api-key-here
WEAVIATE_URL=your-cluster.weaviate.cloud

SUPABASE_API_KEY=your-supabase-service-role-key-here
SUPABASE_URL=https://your-project.supabase.co
DATABASE_URL=postgresql://postgres:password@db.your-project.supabase.co:5432/postgres
```

4. Click **"Add"** for each variable

### Step 4: Get Your URL

1. Go to **"Settings"** → **"Domains"**
2. Click **"Generate Domain"**
3. You'll get a URL like: `https://your-app.up.railway.app`

**Done!** 🎉

---

## Files Created for Railway

✅ `railway.json` - Railway configuration  
✅ `Procfile` - Start command  
✅ `runtime.txt` - Python version  
✅ `requirements.txt` - Dependencies  
✅ `streamlit_app.py` - Dashboard app  

---

## Features

| Feature | Status |
|---------|--------|
| Auto-deploy on push | ✅ |
| Free $5/month credit | ✅ |
| Custom domain | ✅ |
| Environment variables | ✅ |
| Logs & monitoring | ✅ |
| Fast performance | ✅ |

---

## Monitoring

### View Logs:
1. Railway Dashboard
2. Click your app
3. **"Deployments"** tab
4. Click latest deployment
5. View real-time logs

### Check Status:
```
Your app URL → Should show dashboard
```

---

## Updating Your App

Just push to GitHub:
```bash
git add .
git commit -m "Update dashboard"
git push origin main
```

Railway auto-deploys in ~2 minutes! ⚡

---

## Cost Estimation

**Free Tier:** $5 credit/month

**Usage:**
- Streamlit app ~$3-4/month
- **Plenty for testing and demos!**

**Upgrade:** If you need more, starts at $5/month

---

## Troubleshooting

### App not starting?
- Check logs in Railway dashboard
- Verify environment variables are set
- Ensure `requirements.txt` is correct

### Connection errors?
- Update `API_BASE_URL` in variables
- Check firewall settings
- Verify API keys are correct

### Slow performance?
- Railway free tier is faster than Streamlit Cloud
- Consider upgrading if needed

---

## Alternative: Local Testing

Before deploying, test locally:

```bash
# Install dependencies
pip install -r requirements.txt

# Run app
streamlit run streamlit_app.py
```

Open: http://localhost:8501

---

## Comparison

| Platform | Railway | Streamlit Cloud |
|----------|---------|-----------------|
| Speed | ⚡⚡⚡⚡⚡ | ⚡⚡ |
| Setup | 5 min | 10 min |
| Free Tier | $5/month | Unlimited |
| Custom Domain | ✅ | ✅ |
| Auto-deploy | ✅ | ✅ |

---

## Next Steps

1. ✅ Push code to GitHub
2. ✅ Deploy on Railway
3. ✅ Add environment variables
4. ✅ Get public URL
5. ✅ Share with team!

**Railway URL:** https://railway.app  
**Documentation:** https://docs.railway.app

Happy deploying! 🚀
