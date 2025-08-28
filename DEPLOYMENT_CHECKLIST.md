# 🚀 Noah MVP - Complete Deployment Checklist

## ✅ **Pre-Deployment Verification**

### **Local Testing Complete**
- [x] Backend running on port 8000
- [x] Frontend running on port 8502
- [x] All APIs responding (OpenAI, ElevenLabs, Tavily)
- [x] Full workflow tested (news → GPT-4 → TTS → MP3)
- [x] Audio generation working
- [x] MP3 download working

### **Code Ready**
- [x] All files committed to git
- [x] No sensitive data in repository
- [x] Dependencies specified in requirements.txt
- [x] Dockerfile configured for production
- [x] Environment variables properly handled

## 🌐 **Render Deployment Steps**

### **Step 1: Access Render Dashboard**
- [ ] Go to https://dashboard.render.com/
- [ ] Sign in with GitHub account
- [ ] Verify account has access to `noah-mvp` repository

### **Step 2: Create Backend Service**
- [ ] Click **"New +"** → **"Web Service"**
- [ ] Connect GitHub repository: `noah-mvp`
- [ ] **Name**: `noah-api` (or your preferred name)
- [ ] **Environment**: `Python 3`
- [ ] **Region**: Choose closest to your users
- [ ] **Branch**: `main`
- [ ] **Root Directory**: Leave blank (root of repo)

### **Step 3: Configure Build Settings**
- [ ] **Build Command**: `pip install -r requirements.txt`
- [ ] **Start Command**: `uvicorn server:app --host 0.0.0.0 --port $PORT`
- [ ] **Plan**: `Starter` (free tier)

### **Step 4: Set Environment Variables**
Click **"Environment"** tab and add:

| Variable | Value | Notes |
|----------|-------|-------|
| `OPENAI_API_KEY` | `your_actual_key` | From your .env file |
| `ELEVENLABS_API_KEY` | `your_actual_key` | From your .env file |
| `TAVILY_API_KEY` | `your_actual_key` | From your .env file |
| `ELEVENLABS_VOICE_ID` | `21m00Tcm4TlvDq8ikWAM` | Default voice |
| `AUDIO_DIR` | `/tmp` | Temporary storage |
| `ALLOWED_ORIGINS` | `*` | Allow all origins |

### **Step 5: Deploy Backend**
- [ ] Click **"Create Web Service"**
- [ ] Wait for build to complete (2-5 minutes)
- [ ] Verify deployment success
- [ ] **Copy your backend URL** (e.g., `https://noah-api-xyz.onrender.com`)

### **Step 6: Test Backend**
- [ ] Visit your backend URL + `/health`
- [ ] Should see all APIs responding with `true`
- [ ] Test `/voices` endpoint
- [ ] Test `/generate` endpoint with sample data

### **Step 7: Update Frontend Configuration**
- [ ] Update `.env` file with your backend URL:
  ```bash
  API_BASE=https://your-backend-url.onrender.com
  ```
- [ ] Restart local frontend to test connection

### **Step 8: Deploy Frontend (Optional)**
- [ ] Create another Web Service for frontend
- [ ] **Name**: `noah-frontend`
- [ ] **Build Command**: `pip install -r requirements.txt`
- [ ] **Start Command**: `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`
- [ ] **Environment Variables**: Only `API_BASE` pointing to your backend

## 🔧 **Post-Deployment Testing**

### **Backend Health Check**
```bash
curl https://your-backend-url.onrender.com/health
```
Expected response:
```json
{
  "openai": true,
  "elevenlabs": true,
  "tavily": true,
  "ok": true
}
```

### **Generate Test Bulletin**
```bash
curl -X POST "https://your-backend-url.onrender.com/generate" \
  -H "Content-Type: application/json" \
  -d '{"topics":["tech news"],"language":"English","voice":"21m00Tcm4TlvDq8ikWAM","duration":2}'
```

### **Frontend Integration**
- [ ] Open your frontend URL
- [ ] Configure a bulletin (topics, language, voice, duration)
- [ ] Click "Generate"
- [ ] Verify audio generation works
- [ ] Test MP3 download

## 🎯 **Success Criteria**

### **Backend**
- [ ] Health endpoint returns all APIs as `true`
- [ ] Voices endpoint returns list of available voices
- [ ] Generate endpoint creates bulletins successfully
- [ ] Download endpoint serves MP3 files

### **Frontend**
- [ ] Loads without errors
- [ ] Connects to backend successfully
- [ ] Generates bulletins
- [ ] Plays audio
- [ ] Downloads MP3 files

### **Production Features**
- [ ] Available worldwide via HTTPS
- [ ] Handles multiple concurrent users
- [ ] Generates professional-quality audio
- [ ] Provides real-time news content

## 🆘 **Troubleshooting**

### **Common Issues**
1. **Build Failures**: Check requirements.txt and Python version
2. **API Errors**: Verify environment variables are set correctly
3. **Port Conflicts**: Ensure start command uses `$PORT`
4. **Memory Issues**: Upgrade to paid plan if needed

### **Debug Commands**
```bash
# Check backend logs in Render dashboard
# Test API endpoints directly
# Verify environment variables
# Check audio directory permissions
```

## 🎉 **Completion**

Once all steps are completed:
- [ ] Your Noah MVP is live and accessible worldwide
- [ ] Users can generate custom news bulletins
- [ ] Professional TTS audio is generated
- [ ] MP3 files are downloadable
- [ ] System is production-ready and scalable

---

**🎙️ Congratulations! Your Noah MVP is now a professional news bulletin service! 🚀**
