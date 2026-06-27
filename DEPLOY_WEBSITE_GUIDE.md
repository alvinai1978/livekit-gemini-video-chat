# Deploy Guide: LiveKit + Gemini Video Chat Website

This app has 3 running parts:

1. **Frontend** - React/Vite website
2. **Backend** - FastAPI token + Gemini text chat + agent dispatch API
3. **Voice Agent** - Python LiveKit Gemini voice worker

LiveKit Cloud remains your realtime video/audio room server.

---

## Recommended hosting setup

### Option A: Vercel + Render

- Frontend: Vercel
- Backend API: Render Web Service
- Gemini Voice Agent: Render Background Worker
- LiveKit: LiveKit Cloud

This is the easiest setup for a beginner.

---

## Environment variables

### Backend service variables

Set these in your backend hosting dashboard:

```env
LIVEKIT_URL=wss://YOUR-PROJECT.livekit.cloud
LIVEKIT_API_KEY=YOUR_LIVEKIT_API_KEY
LIVEKIT_API_SECRET=YOUR_LIVEKIT_API_SECRET

FRONTEND_ORIGIN=https://YOUR-FRONTEND.vercel.app

GEMINI_API_KEY=YOUR_GEMINI_API_KEY
GOOGLE_API_KEY=YOUR_GEMINI_API_KEY
GEMINI_TEXT_MODEL=gemini-2.5-flash
GEMINI_MAX_OUTPUT_TOKENS=700
GEMINI_TEMPERATURE=0.6
DEBUG_AI_ERRORS=false

LIVEKIT_AGENT_NAME=az-gemini-voice-assistant
```

### Agent worker variables

Set these in your agent/worker hosting dashboard:

```env
LIVEKIT_URL=wss://YOUR-PROJECT.livekit.cloud
LIVEKIT_API_KEY=YOUR_LIVEKIT_API_KEY
LIVEKIT_API_SECRET=YOUR_LIVEKIT_API_SECRET

GOOGLE_API_KEY=YOUR_GEMINI_API_KEY
GEMINI_API_KEY=YOUR_GEMINI_API_KEY

LIVEKIT_AGENT_NAME=az-gemini-voice-assistant
GEMINI_LIVE_MODEL=gemini-3.1-flash-live-preview
GEMINI_LIVE_VOICE=Puck
GEMINI_LIVE_TEMPERATURE=0.7
```

### Frontend variables

Set this in Vercel:

```env
VITE_API_BASE=https://YOUR-BACKEND.onrender.com
```

---

## Render backend settings

If creating manually:

- Root Directory: `backend`
- Runtime: Python
- Build Command: `pip install -r requirements.txt`
- Start Command: `uvicorn app:app --host 0.0.0.0 --port $PORT`

After deploy, test:

```text
https://YOUR-BACKEND.onrender.com/api/health
```

---

## Render voice agent worker settings

If creating manually:

- Root Directory: `agent`
- Runtime: Python
- Build Command: `pip install -r requirements.txt`
- Start Command: `python agent.py start`

Important: the worker must stay running. If the worker is stopped or sleeping, clicking **Start Gemini Voice** from the website cannot bring the voice bot into the room.

---

## Vercel frontend settings

If creating manually:

- Root Directory: `frontend`
- Framework Preset: Vite
- Build Command: `npm run build`
- Output Directory: `dist`

Environment variable:

```env
VITE_API_BASE=https://YOUR-BACKEND.onrender.com
```

After setting `VITE_API_BASE`, redeploy the frontend.

---

## Required production flow

1. Deploy backend first.
2. Copy backend public URL.
3. Put backend URL into Vercel as `VITE_API_BASE`.
4. Deploy frontend.
5. Copy frontend public URL.
6. Put frontend URL into backend as `FRONTEND_ORIGIN`.
7. Deploy voice agent worker.
8. Open frontend website and join a room.
9. Click **Start Gemini Voice**.

---

## Common problems

### Browser cannot use camera/mic

Use an HTTPS website URL. `localhost` is okay for local tests, but a real public website should use HTTPS.

### Frontend says failed to fetch

Check:

- `VITE_API_BASE` points to the backend URL, not the frontend URL.
- Backend CORS has `FRONTEND_ORIGIN=https://your-frontend-domain`.
- Backend `/api/health` opens in browser.

### Gemini text chat works but voice does not

Check:

- Agent worker is running.
- Backend and agent both use same `LIVEKIT_AGENT_NAME`.
- Agent worker has real `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`, and `GOOGLE_API_KEY`.

### Voice agent says failed to connect to LiveKit

Usually wrong LiveKit key/secret or wrong LiveKit URL. Make sure all LiveKit values came from the same LiveKit Cloud project.
