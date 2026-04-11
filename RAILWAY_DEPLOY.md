# Deploy to Railway (2 Minutes)

Railway is the easiest way to deploy this Python backend. No Docker knowledge needed.

## Step 1: Deploy Backend (2 minutes)

1. **Go to https://railway.app**
2. **Click "Start a New Project"**
3. **Select "Deploy from GitHub repo"**
4. **Authorize Railway** to access your GitHub
5. **Select this repository**
6. **Railway auto-detects Python** and starts deploying
7. **Wait 2-3 minutes** for build to complete

## Step 2: Add Environment Variables

1. In Railway dashboard, click your service
2. Go to **Variables** tab
3. Add these variables:
   ```
   GOOGLE_API_KEY=your_gemini_api_key_here
   TAVILY_API_KEY=your_tavily_api_key_here
   ```
4. Service will auto-redeploy

## Step 3: Get Your Backend URL

1. Go to **Settings** tab
2. Click **Generate Domain**
3. Copy the URL (e.g., `https://research-agent-production.up.railway.app`)

## Step 4: Update Frontend

1. In Vercel dashboard, go to your `aria` project
2. Go to **Settings** → **Environment Variables**
3. Add or update:
   ```
   VITE_BACKEND_URL=https://your-railway-url.up.railway.app
   ```
4. Go to **Deployments** → Click ⋯ on latest → **Redeploy**

## Done! 🎉

Your app is now fully deployed:
- **Frontend**: https://aria-omega-liard.vercel.app
- **Backend**: https://your-railway-url.up.railway.app

## Cost

- **Railway**: $5 free credit/month (enough for hobby projects)
- **Vercel**: Free unlimited for personal projects
- **Total**: Effectively free for testing/hobby use

## Why Railway?

✅ No Docker configuration needed  
✅ No Rust compilation issues  
✅ Handles long-running requests (SSE streaming)  
✅ Auto-deploys on git push  
✅ No cold starts  
✅ Perfect for Python + FastAPI  

## Troubleshooting

### Backend not responding
- Check Railway logs in dashboard
- Verify environment variables are set
- Make sure domain is generated

### Frontend can't connect
- Verify `VITE_BACKEND_URL` in Vercel matches Railway domain
- Check CORS settings in `research_agent/config.py`
- Redeploy frontend after changing env vars
