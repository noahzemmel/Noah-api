# 🎙️ Noah MVP - Smart News Bulletin Generator

A fully functional MVP that generates daily smart news bulletins with AI-powered content and professional text-to-speech audio.

## ✨ **Features**

- **📰 Real-time News**: Fetches latest news from Tavily API
- **🧠 AI Content**: GPT-4 powered summarization and expansion
- **🎵 Professional TTS**: ElevenLabs high-quality text-to-speech
- **🎚️ Customizable**: Choose topics, language, voice, and duration
- **📱 Beautiful UI**: Modern Streamlit interface
- **💾 MP3 Download**: Offline listening capability
- **🌍 Multi-language**: Support for multiple languages
- **🎙️ Voice Selection**: 50+ professional voices available

## 🚀 **Quick Start**

### **Local Development**
```bash
# Clone the repository
git clone https://github.com/yourusername/noah-mvp.git
cd noah-mvp

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys

# Start both services
./quick_start.sh
```

### **Production Deployment**
Follow the complete deployment guide: [**DEPLOY_NOW.md**](DEPLOY_NOW.md)

## 🏗️ **Architecture**

- **Backend**: FastAPI with async processing
- **Frontend**: Streamlit with real-time updates
- **AI**: OpenAI GPT-4 for content generation
- **TTS**: ElevenLabs for professional audio
- **News**: Tavily API for real-time content
- **Storage**: Temporary MP3 file storage

## 📋 **API Endpoints**

- `GET /health` - Service health check
- `GET /voices` - Available TTS voices
- `POST /generate` - Generate news bulletin
- `GET /download/{filename}` - Download MP3 file
- `GET /docs` - Interactive API documentation

## 🔧 **Configuration**

### **Required Environment Variables**
```bash
OPENAI_API_KEY=your_openai_api_key
ELEVENLABS_API_KEY=your_elevenlabs_api_key
TAVILY_API_KEY=your_tavily_api_key
ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM
```

### **Optional Variables**
```bash
API_BASE=http://localhost:8000
AUDIO_DIR=./audio
ALLOWED_ORIGINS=*
```

## 🎯 **Usage**

1. **Configure**: Select topics, language, voice, and duration
2. **Generate**: Click "Generate Bulletin" to create content
3. **Listen**: Play the generated audio directly in the browser
4. **Download**: Save MP3 files for offline listening

## 📚 **Documentation**

- [**DEPLOY_NOW.md**](DEPLOY_NOW.md) - Complete deployment guide
- [**DEPLOYMENT_CHECKLIST.md**](DEPLOYMENT_CHECKLIST.md) - Step-by-step checklist
- [**FINAL_STATUS.md**](FINAL_STATUS.md) - Current system status

## 🧪 **Testing**

### **Local Testing**
```bash
# Start services
./quick_start.sh

# Test backend
curl http://localhost:8000/health

# Test frontend
open http://localhost:8502
```

### **Production Testing**
```bash
# Health check
curl https://your-service.onrender.com/health

# Generate bulletin
curl -X POST "https://your-service.onrender.com/generate" \
  -H "Content-Type: application/json" \
  -d '{"topics":["tech news"],"language":"English","voice":"21m00Tcm4TlvDq8ikWAM","duration":3}'
```

## 🚀 **Deployment Status**

- ✅ **Local Development**: Fully operational
- ✅ **API Integration**: All services connected
- ✅ **Audio Generation**: MP3 creation working
- ✅ **Frontend UI**: Beautiful interface ready
- 🎯 **Production**: Ready for Render deployment

## 🆘 **Troubleshooting**

### **Common Issues**
1. **API Keys**: Ensure all environment variables are set
2. **Port Conflicts**: Use different ports if 8000/8502 are busy
3. **Dependencies**: Install all requirements with `pip install -r requirements.txt`
4. **Audio Files**: Check audio directory permissions

### **Getting Help**
- Check the deployment guides
- Review environment variable configuration
- Test individual API endpoints
- Check service logs

## 📄 **License**

This project is licensed under the MIT License.

---

## 🎉 **Ready to Deploy!**

Your Noah MVP is fully functional and ready for production deployment. Follow [**DEPLOY_NOW.md**](DEPLOY_NOW.md) to get it live on Render!

**Status**: 🟢 **PRODUCTION READY**
