import datetime
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Literal
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from livekit import api
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

load_dotenv()

app = FastAPI(title="LiveKit Video Chat + Gemini AI Chat + Gemini Voice Agent Server")


def parse_cors_origins() -> list[str]:
    """Allowed browser origins for local + production frontend.

    Local default works for Vite. For a real website, set FRONTEND_ORIGIN or
    ALLOWED_ORIGINS to your deployed frontend URL, for example:
    FRONTEND_ORIGIN=https://your-app.vercel.app
    """
    configured = os.getenv("ALLOWED_ORIGINS") or os.getenv("FRONTEND_ORIGIN") or ""
    origins = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
    for item in configured.split(","):
        origin = item.strip().rstrip("/")
        if origin and origin not in origins:
            origins.append(origin)
    return origins


app.add_middleware(
    CORSMiddleware,
    allow_origins=parse_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"ok": True, "service": "livekit-gemini-backend", "health": "/api/health"}


class TokenRequest(BaseModel):
    room_name: str = Field(default="demo-room", max_length=100)
    participant_name: str = Field(default="Guest", max_length=60)


class AgentDispatchRequest(BaseModel):
    room_name: str = Field(default="demo-room", max_length=100)
    participant_name: str = Field(default="Guest", max_length=60)


class AIMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class AIChatRequest(BaseModel):
    room_name: str = Field(default="demo-room", max_length=100)
    participant_name: str = Field(default="Guest", max_length=60)
    message: str = Field(min_length=1, max_length=4000)
    history: list[AIMessage] = Field(default_factory=list)


def safe_text(value: str | None, fallback: str, max_len: int = 80) -> str:
    """Keep names simple so they are safe for room/identity use."""
    cleaned = re.sub(r"[^a-zA-Z0-9_\- ]", "", value or "").strip()
    return (cleaned[:max_len] or fallback)


def safe_room_name(value: str | None) -> str:
    return safe_text(value, "demo-room", max_len=100).replace(" ", "-")


def get_env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def first_env(*names: str) -> str | None:
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return None


def livekit_credentials() -> tuple[str, str, str]:
    livekit_url = os.getenv("LIVEKIT_URL")
    api_key = os.getenv("LIVEKIT_API_KEY")
    api_secret = os.getenv("LIVEKIT_API_SECRET")

    if not livekit_url or not api_key or not api_secret:
        raise HTTPException(
            status_code=500,
            detail="Missing LIVEKIT_URL, LIVEKIT_API_KEY, or LIVEKIT_API_SECRET in backend .env",
        )

    return livekit_url, api_key, api_secret


def gemini_api_key() -> str:
    # Google GenAI SDK commonly uses GEMINI_API_KEY.
    # LiveKit Google plugin commonly uses GOOGLE_API_KEY.
    # Support both so you can paste either one into .env.
    key = first_env("GEMINI_API_KEY", "GOOGLE_API_KEY")
    if not key:
        raise HTTPException(
            status_code=500,
            detail="Missing GEMINI_API_KEY or GOOGLE_API_KEY in backend .env. Add your Google AI Studio API key first.",
        )
    return key


@app.get("/api/health")
async def health_check():
    gemini_key = bool(first_env("GEMINI_API_KEY", "GOOGLE_API_KEY"))
    return {
        "ok": True,
        "livekit_configured": bool(
            os.getenv("LIVEKIT_URL")
            and os.getenv("LIVEKIT_API_KEY")
            and os.getenv("LIVEKIT_API_SECRET")
        ),
        "ai_provider": "google-gemini",
        "ai_chat_configured": gemini_key,
        "ai_chat_model": os.getenv("GEMINI_TEXT_MODEL", "gemini-2.5-flash"),
        "voice_agent_name": os.getenv("LIVEKIT_AGENT_NAME", "az-gemini-voice-assistant"),
        "voice_agent_model": os.getenv("GEMINI_LIVE_MODEL", "gemini-2.5-flash-native-audio-preview-12-2025"),
        "voice_agent_voice": os.getenv("GEMINI_LIVE_VOICE", "Puck"),
    }


@app.post("/api/token", status_code=201)
async def create_token(payload: TokenRequest):
    livekit_url, api_key, api_secret = livekit_credentials()

    room_name = safe_room_name(payload.room_name)
    participant_name = safe_text(payload.participant_name, "Guest", max_len=60)
    identity_base = participant_name.lower().replace(" ", "-")
    participant_identity = f"{identity_base}-{uuid4().hex[:8]}"

    token = (
        api.AccessToken(api_key, api_secret)
        .with_identity(participant_identity)
        .with_name(participant_name)
        .with_ttl(datetime.timedelta(hours=6))
        .with_grants(
            api.VideoGrants(
                room_join=True,
                room=room_name,
                can_publish=True,
                can_subscribe=True,
                can_publish_data=True,
            )
        )
    )

    return {
        "server_url": livekit_url,
        "participant_token": token.to_jwt(),
        "room_name": room_name,
        "participant_identity": participant_identity,
        "participant_name": participant_name,
    }


@app.post("/api/dispatch-agent")
async def dispatch_agent(payload: AgentDispatchRequest):
    """Ask LiveKit to place the configured Python Gemini voice agent into this room."""
    livekit_url, api_key, api_secret = livekit_credentials()
    room_name = safe_room_name(payload.room_name)
    participant_name = safe_text(payload.participant_name, "Guest", max_len=60)
    agent_name = safe_text(os.getenv("LIVEKIT_AGENT_NAME"), "az-gemini-voice-assistant", max_len=80)

    metadata = json.dumps(
        {
            "source": "livekit-video-chat-web-app",
            "provider": "google-gemini",
            "requested_by": participant_name,
            "room_name": room_name,
        }
    )

    lkapi = api.LiveKitAPI(livekit_url, api_key, api_secret)
    try:
        # Avoid accidental duplicate voice bots when the user clicks the button again.
        try:
            existing_dispatches = await lkapi.agent_dispatch.list_dispatch(room_name=room_name)
            for dispatch in existing_dispatches:
                if getattr(dispatch, "agent_name", "") == agent_name:
                    return {
                        "ok": True,
                        "already_dispatched": True,
                        "agent_name": agent_name,
                        "room_name": room_name,
                        "message": "Gemini Voice AI already requested for this room.",
                    }
        except Exception:
            # Listing may fail before a room is fully created in some local/dev cases.
            # The create_dispatch call below is the important operation.
            pass

        dispatch = await lkapi.agent_dispatch.create_dispatch(
            api.CreateAgentDispatchRequest(
                agent_name=agent_name,
                room=room_name,
                metadata=metadata,
            )
        )

        return {
            "ok": True,
            "already_dispatched": False,
            "agent_name": agent_name,
            "room_name": room_name,
            "dispatch_id": getattr(dispatch, "id", None) or getattr(dispatch, "dispatch_id", ""),
            "message": "Gemini Voice AI dispatch requested. Make sure the Python agent service is running.",
        }
    except HTTPException:
        raise
    except Exception as exc:
        show_details = get_env_bool("DEBUG_AI_ERRORS", default=False)
        detail = str(exc) if show_details else (
            "Could not dispatch Gemini voice agent. Check that the agent service is running, "
            "LIVEKIT_AGENT_NAME matches, and LiveKit credentials are correct."
        )
        raise HTTPException(status_code=500, detail=detail) from exc
    finally:
        await lkapi.aclose()


def build_gemini_prompt(payload: AIChatRequest) -> str:
    room_name = safe_room_name(payload.room_name)
    participant_name = safe_text(payload.participant_name, "Guest", max_len=60)

    lines: list[str] = [
        "You are an AI assistant inside a LiveKit video chat web app.",
        f"The current room is: {room_name}.",
        f"The current user is: {participant_name}.",
        "",
        "Behavior:",
        "- Reply in the same language as the user. If the user uses Tagalog/Taglish, answer in Tagalog/Taglish.",
        "- Keep answers clear, practical, and not too long unless the user asks for details.",
        "- You are currently a typed chat assistant powered by Google Gemini.",
        "- If the user wants voice, tell them to start the Gemini Voice AI agent.",
        "- Do not claim that you can see the video, hear the microphone, or control the LiveKit room from this chat panel.",
        "- If the user asks for medical, legal, financial, or safety-critical advice, give careful general guidance and suggest consulting a qualified professional.",
        "",
        "Recent chat history:",
    ]

    for item in payload.history[-12:]:
        content = item.content.strip()
        if content:
            label = "User" if item.role == "user" else "Assistant"
            lines.append(f"{label}: {content[:4000]}")

    lines.extend([
        "",
        f"User: {payload.message.strip()[:4000]}",
        "Assistant:",
    ])
    return "\n".join(lines)


def extract_gemini_text(data: dict) -> str:
    """Extract text from a Gemini generateContent REST response."""
    texts: list[str] = []
    for candidate in data.get("candidates", []):
        content = candidate.get("content", {}) or {}
        for part in content.get("parts", []) or []:
            text = part.get("text")
            if text:
                texts.append(text)
    return "\n".join(texts).strip()


def generate_ai_reply(payload: AIChatRequest) -> dict[str, str]:
    """Send typed chat to Gemini using REST.

    This avoids `from google import genai` import errors on Windows when the
    local environment has the wrong Google package installed or dependencies
    were installed outside the active virtual environment.
    """
    api_key = gemini_api_key()
    model = os.getenv("GEMINI_TEXT_MODEL", "gemini-2.5-flash").strip()
    model = model.removeprefix("models/")
    max_output_tokens = int(os.getenv("GEMINI_MAX_OUTPUT_TOKENS", "700"))
    temperature = float(os.getenv("GEMINI_TEMPERATURE", "0.6"))

    body = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": build_gemini_prompt(payload)}],
            }
        ],
        "generationConfig": {
            "maxOutputTokens": max_output_tokens,
            "temperature": temperature,
        },
    }

    endpoint = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{urllib.parse.quote(model, safe='')}:generateContent"
    )
    url = endpoint + "?" + urllib.parse.urlencode({"key": api_key})

    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            error_data = json.loads(raw)
            message = error_data.get("error", {}).get("message", raw)
        except json.JSONDecodeError:
            message = raw
        raise RuntimeError(f"Gemini API error: {message}") from exc

    reply = extract_gemini_text(data)
    if not reply:
        reply = "Pasensya, walang malinaw na sagot ang Gemini. Subukan mong ulitin ang tanong."

    return {"reply": reply, "model": model, "provider": "google-gemini-rest"}


@app.post("/api/ai-chat")
async def ai_chat(payload: AIChatRequest):
    try:
        return await run_in_threadpool(generate_ai_reply, payload)
    except HTTPException:
        raise
    except Exception as exc:
        show_details = get_env_bool("DEBUG_AI_ERRORS", default=False)
        detail = str(exc) if show_details else "Gemini request failed. Check your GEMINI_API_KEY / GOOGLE_API_KEY and model access settings."
        raise HTTPException(status_code=500, detail=detail) from exc
