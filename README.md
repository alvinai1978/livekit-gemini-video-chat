# LiveKit Video Chat + Gemini AI + Web Deployment Ready

This package includes:

- React/Vite frontend
- Python FastAPI backend
- Python LiveKit Gemini voice agent
- Windows local run scripts
- Dockerfiles for backend and agent
- Render blueprint sample
- Vercel config sample
- Deployment guide

Start with `DEPLOY_WEBSITE_GUIDE.md` for production website setup.

## Local quick start

### Backend

```powershell
cd backend
copy .env.example .env
notepad .env
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install -r requirements.txt
python -m uvicorn app:app --reload --host 127.0.0.1 --port 8000
```

### Frontend

```powershell
cd frontend
copy .env.example .env
npm install
npm run dev
```

### Agent

```powershell
cd agent
copy .env.example .env
notepad .env
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install -r requirements.txt
python agent.py dev
```
