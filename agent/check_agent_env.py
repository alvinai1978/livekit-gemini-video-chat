import os
from pathlib import Path
from dotenv import dotenv_values, load_dotenv

root = Path(__file__).resolve().parent.parent
backend_env = root / "backend" / ".env"
agent_env = Path(__file__).resolve().parent / ".env"

def is_placeholder(v):
    if v is None:
        return True
    v = str(v).strip()
    return not v or "YOUR_" in v or "YOUR-" in v or "xxxxxxxx" in v

load_dotenv(backend_env, override=False)
for k, v in dotenv_values(agent_env).items():
    if k and not is_placeholder(v):
        os.environ[k] = v or ""
if os.getenv("GEMINI_API_KEY") and not os.getenv("GOOGLE_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = os.getenv("GEMINI_API_KEY")

required = ["LIVEKIT_URL", "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET", "GOOGLE_API_KEY", "LIVEKIT_AGENT_NAME", "GEMINI_LIVE_MODEL"]
print("Voice Agent Environment Check")
print("-" * 36)
ok = True
for key in required:
    val = os.getenv(key, "")
    if is_placeholder(val):
        status = "MISSING / PLACEHOLDER"
        ok = False
    else:
        if key.endswith("SECRET") or key.endswith("KEY"):
            status = "OK (hidden)"
        else:
            status = f"OK ({val})"
    print(f"{key}: {status}")
if not ok:
    raise SystemExit("\nFix the values in backend/.env and agent/.env before starting the voice agent.")
print("\nOK: required environment values look set.")
