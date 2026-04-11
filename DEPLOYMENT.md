# Deployment Guide

## Backend Deployment Options

### Option 1: Railway (Recommended - Easiest)

Railway handles Python dependencies better and has no cold starts on free tier.

1. Go to [railway.app](https://railway.app) and sign up with GitHub
2. Click **"New Project"** → **"Deploy from GitHub repo"**
3. Select your repository
4. Railway will auto-detect Python and deploy
5. Add environment variables:
   - `GOOGLE_API_KEY` = your Gemini API key
   - `TAVILY_API_KEY` = your Tavily API key
6. Get your URL: `https://your-app.up.railway.app`

**Cost**: $5 free credit/month (enough for hobby projects)

---

### Option 2: Render (Free with Cold Starts)

If you're getting Rust compilation errors on Render, try these fixes:

#### Fix 1: Use Docker Deployment

Create `research_agent/Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Then in Render:
- Choose **"Docker"** instead of Python
- Render will use the Dockerfile

#### Fix 2: Pin Dependencies

Update `requirements.txt` to use specific versions that don't require Rust:

```txt
fastapi==0.115.0
uvicorn[standard]==0.30.6
langgraph==0.2.28
langchain==0.3.0
langchain-google-genai==2.0.0
langchain-core==0.3.0
tavily-python==0.5.0
pydantic==2.9.0
pydantic-settings==2.5.0
python-dotenv==1.0.1
structlog==24.4.0
httpx==0.27.2
sse-starlette==2.1.3
```

---

### Option 3: Fly.io (Free Tier Available)

1. Install Fly CLI: `curl -L https://fly.io/install.sh | sh`
2. Login: `fly auth login`
3. From `research_agent` folder:
   ```bash
   fly launch
   fly secrets set GOOGLE_API_KEY=your_key
   fly secrets set TAVILY_API_KEY=your_key
   fly deploy
   ```

---

## Frontend Deployment (Vercel)

### Step 1: Update Backend URL

1. Copy your Render backend URL
2. Update `aria/.env.production`:

```env
VITE_BACKEND_URL=https://your-backend-url.onrender.com
```

### Step 2: Configure Vercel Environment Variable

In your Vercel project dashboard:
1. Go to **Settings** → **Environment Variables**
2. Add:
   - **Key**: `VITE_BACKEND_URL`
   - **Value**: `https://your-backend-url.onrender.com`
   - **Environment**: Production

### Step 3: Redeploy Frontend

```bash
cd aria
npm run build
vercel --prod
```

---

## Alternative: Quick Local Test

To test locally before deploying:

### Terminal 1 - Backend
```bash
cd research_agent
pip install -r requirements.txt
# Create .env file with your API keys
python main.py
```

### Terminal 2 - Frontend
```bash
cd aria
npm install
npm run dev
```

Visit: http://localhost:3000

---

## Troubleshooting

### Backend Connection Failed

1. Check backend is running: Visit `https://your-backend-url.onrender.com/docs`
2. Check CORS settings in `research_agent/config.py`
3. Verify environment variables are set in Render
4. Check Render logs for errors

### Frontend Not Connecting

1. Verify `VITE_BACKEND_URL` is set correctly
2. Check browser console for CORS errors
3. Ensure backend URL doesn't have trailing slash
4. Rebuild and redeploy frontend after changing env vars

---

## Cost

- **Render Free Tier**: Backend sleeps after 15 min of inactivity (cold start ~30s)
- **Vercel Free Tier**: Unlimited bandwidth for personal projects
- **Total**: $0/month for hobby projects

For production with no cold starts, upgrade Render to $7/month.
