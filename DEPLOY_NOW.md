# 🚀 DEPLOY NOAH TO RENDER NOW

## ✅ **Pre-Deployment Checklist - COMPLETED**
- [x] All API keys working (OpenAI, ElevenLabs, Tavily)
- [x] Local testing successful
- [x] Full workflow tested (news → GPT-4 → TTS → MP3)
- [x] Environment variables configured
- [x] Code ready for production
- [x] **FIXED**: Python 3.13 compatibility issues

## 🌐 **Deploy to Render - Step by Step**

### **1. Go to Render Dashboard**
- Visit: https://dashboard.render.com/
- Sign in with your GitHub account

### **2. Create Backend Service**
- Click **"New +"** → **"Web Service"**
- **Connect your GitHub repository**: `noah-mvp`
- **Name**: `noah-api` (or your preferred name)
- **Environment**: `Python 3` (will use Python 3.11 from runtime.txt)
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn server:app --host 0.0.0.0 --port $PORT`
- **Plan**: `Starter` (free tier)

### **3. Set Environment Variables**
Click **"Environment"** and add these EXACTLY:

```
OPENAI_API_KEY=your_openai_api_key_here
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here
ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM
TAVILY_API_KEY=your_tavily_api_key_here
AUDIO_DIR=/tmp
ALLOWED_ORIGINS=*
```

**Important**: Replace the placeholder values with your actual API keys from your `.env` file.

### **4. Deploy Backend**
- Click **"Create Web Service"**
- Wait for deployment (usually 2-5 minutes)
- **Copy your backend URL** (e.g., `https://noah-api-xyz.onrender.com`)

### **5. Update Frontend Configuration**
Once backend is deployed, update your `.env` file:
```bash
API_BASE=https://your-backend-url.onrender.com
```

### **6. Test Backend**
Visit your backend URL + `/health` to verify it's working:
```
https://your-backend-url.onrender.com/health
```

You should see:
```json
{
  "openai": true,
  "elevenlabs": true,
  "tavily": true,
  "ok": true
}
```

### **7. Deploy Frontend (Optional)**
If you want the frontend on Render too:
- Create another Web Service
- **Name**: `noah-frontend`
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`
- **Environment Variables**: Only need `API_BASE` pointing to your backend

## 🔧 **What We Fixed**

### **Python 3.13 Compatibility**
- ✅ Added `runtime.txt` to force Python 3.11
- ✅ Updated `requirements.txt` for better compatibility
- ✅ Fixed `pydub` dependency issues
- ✅ Updated Dockerfile for Render deployment

### **Dependencies**
- ✅ All packages compatible with Render's environment
- ✅ Proper system dependencies (ffmpeg, etc.)
- ✅ Clean, organized requirements

## 🎯 **What You'll Get**

### **Backend API**
- **Health Check**: `/health`
- **Generate Bulletin**: `/generate`
- **Download Audio**: `/download/{filename}`
- **Get Voices**: `/voices`
- **API Docs**: `/docs`

### **Frontend**
- Beautiful Streamlit interface
- Voice selection
- Language options
- Duration control
- Real-time generation
- Audio playback & download

## 🔧 **Post-Deployment Testing**

### **Test 1: Health Check**
```bash
curl https://your-backend-url.onrender.com/health
```

### **Test 2: Generate Bulletin**
```bash
curl -X POST "https://your-backend-url.onrender.com/generate" \
  -H "Content-Type: application/json" \
  -d '{"topics":["tech news"],"language":"English","voice":"21m00Tcm4TlvDq8ikWAM","duration":3}'
```

### **Test 3: Frontend Access**
- Visit your frontend URL
- Configure a bulletin
- Click "Generate"
- Verify audio generation works

## 🎉 **You're Done!**

Your Noah MVP will be fully functional with:
- ✅ Real-time news fetching
- ✅ AI-powered content generation
- ✅ Professional TTS audio
- ✅ Beautiful web interface
- ✅ MP3 downloads
- ✅ Production-ready deployment
- ✅ **Fixed Python 3.13 compatibility**

## 🆘 **Need Help?**

If anything goes wrong:
1. Check Render logs
2. Verify environment variables
3. Test API endpoints individually
4. Check the health endpoint
5. **The Python 3.13 issue is now fixed!**

---

**Your Noah MVP is ready to go live! 🚀**
