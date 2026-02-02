# 🚂 Deploy FastAPI Backend to Railway

## Quick Setup

### Step 1: في Railway Dashboard

1. اذهب إلى project الحالي: `pyxon-ai-entry-task`
2. اضغط **"+ New"** في الأعلى
3. اختر **"Empty Service"**
4. سمّيه: `ai-parser-api`

### Step 2: Settings Configuration

في الـ service الجديد:

1. اضغط **"Settings"**
2. **Source**: 
   - Connect GitHub repo: `pyxon-ai-entry-task`
   - Branch: `AI-Parser-01` (or `main`)
3. **Root Directory**: اتركه فارغ (or `/`)
4. **Build Command**: 
   ```
   pip install -r requirements-api.txt
   ```
5. **Start Command**:
   ```
   cd src && uvicorn main:app --host 0.0.0.0 --port $PORT
   ```

### Step 3: Environment Variables

أضف كل هذه الـ variables:

```env
APP_NAME=AI-Parser
APP_VERSION=0.1

GEMINI_API_KEY=your-gemini-api-key
COHERE_API_KEY=your-cohere-api-key

WEAVIATE_API_KEY=your-weaviate-api-key
WEAVIATE_URL=your-cluster.weaviate.cloud

SUPABASE_API_KEY=your-supabase-key
SUPABASE_URL=https://your-project.supabase.co
DATABASE_URL=postgresql://user:pass@db.your-project.supabase.co:5432/postgres

FILE_ALLOWED_TYPES=["text/plain","application/pdf","application/vnd.openxmlformats-officedocument.wordprocessingml.document"]
FILE_MAX_SIZE=10485760
FILE_DEFAULT_CHUNK_SIZE=512000
```

### Step 4: Deploy

1. اضغط **"Deploy"**
2. انتظر البناء (2-3 دقائق)
3. شوف الـ logs

### Step 5: احصل على FastAPI URL

1. في Settings → **"Networking"**
2. اضغط **"Generate Domain"**
3. انسخ الـ URL (مثل: `https://ai-parser-api-production.up.railway.app`)

### Step 6: حدّث Streamlit Service

في الـ Streamlit service (الأول):

1. اذهب إلى **"Variables"**
2. عدّل `API_BASE_URL`:
   ```
   API_BASE_URL=https://ai-parser-api-production.up.railway.app
   ```
3. اضغط Save → سيعيد deploy تلقائياً

### Step 7: اختبر!

1. افتح FastAPI URL: `https://your-api.railway.app/docs`
2. المفروض تشوف Swagger docs ✅
3. افتح Streamlit URL
4. المفروض Dashboard يشتغل ويتصل بالـ API! 🎉

---

## ملاحظات مهمة:

✅ **Service 1 (Streamlit Dashboard):**
- يعرض الواجهة
- يحتاج فقط: `requirements.txt` (streamlit, plotly, etc.)

✅ **Service 2 (FastAPI Backend):**
- يشغّل الـ API endpoints
- يحتاج: `requirements-api.txt` (fastapi, uvicorn, etc.)

✅ **الاتصال:**
```
User → Streamlit → FastAPI → Weaviate + Supabase
```

---

## Troubleshooting

### Build Failed?
- تأكد Root Directory صحيح
- تأكد `requirements-api.txt` موجود

### Connection Error?
- تأكد إن `API_BASE_URL` في Streamlit صحيح
- تأكد FastAPI service online

### 404 Errors?
- شيك FastAPI docs: `/docs`
- تأكد الـ routes موجودة

---

**الآن ابدأ الخطوات في Railway!** 🚀
