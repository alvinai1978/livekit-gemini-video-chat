import sys
print('Python:', sys.executable)
try:
    from livekit import agents
    print('OK livekit.agents:', agents.__file__)
except Exception as exc:
    print('FAILED livekit.agents:', repr(exc))
try:
    from livekit.plugins import google
    print('OK livekit.plugins.google:', google.__file__)
except Exception as exc:
    print('FAILED livekit.plugins.google:', repr(exc))
