import json
import os
from pathlib import Path

from dotenv import dotenv_values, load_dotenv
from livekit import agents
from livekit.agents import Agent, AgentServer, AgentSession
from livekit.plugins import google

# Load backend/.env first so the agent can reuse your working LiveKit credentials.
# Then load agent/.env manually, but DO NOT let placeholder values like
# YOUR_LIVEKIT_API_KEY overwrite real values from backend/.env.
CURRENT_DIR = Path(__file__).resolve().parent
ROOT_DIR = CURRENT_DIR.parent
BACKEND_ENV = ROOT_DIR / "backend" / ".env"
AGENT_ENV = CURRENT_DIR / ".env"


def is_placeholder(value: str | None) -> bool:
    if value is None:
        return True
    v = value.strip()
    return (
        not v
        or "YOUR_" in v
        or "YOUR-" in v
        or v in {"sk-your-openai-api-key", "your-gemini-api-key", "AIzaSyxxxxxxxxxxxxxxxxxxxx"}
    )


load_dotenv(BACKEND_ENV, override=False)
for key, value in dotenv_values(AGENT_ENV).items():
    if key and not is_placeholder(value):
        os.environ[key] = value or ""

# Google GenAI SDK commonly uses GEMINI_API_KEY.
# LiveKit Google plugin expects GOOGLE_API_KEY. Mirror either variable.
if os.getenv("GEMINI_API_KEY") and not os.getenv("GOOGLE_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = os.getenv("GEMINI_API_KEY", "")
if os.getenv("GOOGLE_API_KEY") and not os.getenv("GEMINI_API_KEY"):
    os.environ["GEMINI_API_KEY"] = os.getenv("GOOGLE_API_KEY", "")

required_env = ["LIVEKIT_URL", "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET", "GOOGLE_API_KEY"]
bad_env = [k for k in required_env if is_placeholder(os.getenv(k))]
if bad_env:
    print("\nENV ERROR: The voice agent is missing real values for:")
    for k in bad_env:
        print(f"  - {k}")
    print("\nFix: copy your real values from backend/.env into agent/.env, or run:")
    print(r'  cd "D:\Livekits Chat ai\agent"')
    print(r"  copy /Y ..\backend\.env .env")
    print("\nDo not leave values like YOUR_LIVEKIT_API_KEY or YOUR_GEMINI_API_KEY.\n")
    raise SystemExit(1)

AGENT_NAME = os.getenv("LIVEKIT_AGENT_NAME", "az-gemini-voice-assistant")
GEMINI_LIVE_MODEL = os.getenv("GEMINI_LIVE_MODEL", "gemini-3.1-flash-live-preview")
GEMINI_LIVE_VOICE = os.getenv("GEMINI_LIVE_VOICE", "Puck")
GEMINI_LIVE_TEMPERATURE = float(os.getenv("GEMINI_LIVE_TEMPERATURE", "0.7"))


class AZGeminiVoiceAssistant(Agent):
    def __init__(self, requested_by: str = "user", room_name: str = "room") -> None:
        super().__init__(
            instructions=f"""
You are the Gemini voice AI assistant inside a LiveKit video room.
The current room is {room_name}.
You were started by {requested_by}.

Behavior:
- Speak naturally and briefly unless the user asks for detailed steps.
- Reply in the user's language. If they speak Tagalog or Taglish, answer in Tagalog/Taglish.
- You can hear the user's voice in this room, but do not claim you can see video unless video input is explicitly enabled later.
- Be useful for customer support, online consultation, tutorial sessions, meetings, and technical help.
- If you are not sure, say so clearly and ask for the missing detail.
- Avoid markdown-heavy answers because you are speaking aloud.
- For medical, legal, financial, or safety-critical topics, give general guidance and recommend a qualified professional.
""".strip()
        )


def read_metadata(ctx: agents.JobContext) -> dict:
    raw_metadata = getattr(getattr(ctx, "job", None), "metadata", "") or ""
    try:
        return json.loads(raw_metadata) if raw_metadata else {}
    except json.JSONDecodeError:
        return {}


server = AgentServer()


@server.rtc_session(agent_name=AGENT_NAME)
async def entrypoint(ctx: agents.JobContext):
    metadata = read_metadata(ctx)
    requested_by = metadata.get("requested_by", "user")
    room_name = metadata.get("room_name", "room")

    session = AgentSession(
        llm=google.realtime.RealtimeModel(
            model=GEMINI_LIVE_MODEL,
            voice=GEMINI_LIVE_VOICE,
            temperature=GEMINI_LIVE_TEMPERATURE,
        )
    )

    await session.start(
        room=ctx.room,
        agent=AZGeminiVoiceAssistant(requested_by=requested_by, room_name=room_name),
    )

    # This greeting may be ignored by some Gemini Live model versions.
    # If ignored, simply speak to the bot after it joins the room.
    await session.generate_reply(
        instructions=(
            "Greet the room in Tagalog/Taglish. Say that Gemini Voice AI is ready, "
            "and tell the user they can speak now. Keep it under two sentences."
        )
    )


if __name__ == "__main__":
    agents.cli.run_app(server)
