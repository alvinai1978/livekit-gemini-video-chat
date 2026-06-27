import { useMemo, useRef, useState } from 'react';
import { LiveKitRoom, VideoConference } from '@livekit/components-react';
import '@livekit/components-styles';

const API_BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000';

function initialRoomName() {
  const params = new URLSearchParams(window.location.search);
  return params.get('room') || 'demo-room';
}

function nowTime() {
  return new Intl.DateTimeFormat('en-PH', {
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date());
}

function AIChatPanel({ roomName, participantName, voiceStatus }) {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content:
        'Hi! Ako ang Gemini AI assistant ng room na ito. Pwede kang mag-type ng tanong dito, or i-start ang Gemini Voice AI para makausap mo gamit mic.',
      time: nowTime(),
    },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const inputRef = useRef(null);

  async function askAI(event) {
    event.preventDefault();
    const question = input.trim();

    if (!question || loading) {
      return;
    }

    setError('');
    setInput('');

    const userMessage = {
      role: 'user',
      content: question,
      time: nowTime(),
    };

    const historyForApi = messages
      .filter((message) => message.role === 'user' || message.role === 'assistant')
      .slice(-12)
      .map((message) => ({
        role: message.role,
        content: message.content,
      }));

    setMessages((current) => [...current, userMessage]);
    setLoading(true);

    try {
      const response = await fetch(`${API_BASE}/api/ai-chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          room_name: roomName,
          participant_name: participantName,
          message: question,
          history: historyForApi,
        }),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || 'Hindi sumagot ang Gemini AI.');
      }

      setMessages((current) => [
        ...current,
        {
          role: 'assistant',
          content: data.reply,
          model: data.model,
          provider: data.provider,
          time: nowTime(),
        },
      ]);
    } catch (err) {
      setError(err.message || 'May error sa Gemini AI chat.');
      setMessages((current) => [
        ...current,
        {
          role: 'assistant',
          content:
            'Hindi pa ako makasagot ngayon. I-check ang backend .env kung may GEMINI_API_KEY o GOOGLE_API_KEY at tama ang Gemini model.',
          time: nowTime(),
        },
      ]);
    } finally {
      setLoading(false);
      window.setTimeout(() => inputRef.current?.focus(), 50);
    }
  }

  function clearChat() {
    setError('');
    setMessages([
      {
        role: 'assistant',
        content: 'New Gemini AI chat started. Ano ang gusto mong itanong?',
        time: nowTime(),
      },
    ]);
  }

  return (
    <aside className="aiPanel" aria-label="Gemini AI Assistant">
      <div className="aiPanelHeader">
        <div>
          <span className="aiBadge">Gemini AI</span>
          <h3>Ask Gemini</h3>
        </div>
        <button className="ghostButton" onClick={clearChat} type="button">
          Clear
        </button>
      </div>

      <div className="aiHint">
        <strong>Typed Gemini:</strong> dito lalabas ang text answers. <br />
        <strong>Gemini Voice:</strong> {voiceStatus || 'hindi pa naka-start.'}
      </div>

      {error && <div className="aiError">{error}</div>}

      <div className="aiMessages" aria-live="polite">
        {messages.map((message, index) => (
          <article className={`aiMessage ${message.role}`} key={`${message.role}-${index}`}>
            <div className="aiMessageMeta">
              <strong>{message.role === 'user' ? participantName || 'You' : 'Gemini'}</strong>
              <span>{message.time}</span>
            </div>
            <p>{message.content}</p>
            {message.model && <small>Model: {message.model}</small>}
          </article>
        ))}

        {loading && (
          <article className="aiMessage assistant loadingBubble">
            <div className="aiMessageMeta">
              <strong>Gemini</strong>
              <span>{nowTime()}</span>
            </div>
            <p>Nag-iisip...</p>
          </article>
        )}
      </div>

      <form className="aiForm" onSubmit={askAI}>
        <textarea
          ref={inputRef}
          value={input}
          onChange={(event) => setInput(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter' && !event.shiftKey) {
              event.preventDefault();
              askAI(event);
            }
          }}
          placeholder="Magtanong sa Gemini..."
          rows={3}
        />
        <button type="submit" disabled={loading || !input.trim()}>
          {loading ? 'Sending...' : 'Send'}
        </button>
      </form>
    </aside>
  );
}

export default function App() {
  const [roomName, setRoomName] = useState(initialRoomName());
  const [participantName, setParticipantName] = useState('');
  const [connection, setConnection] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [copied, setCopied] = useState(false);
  const [aiOpen, setAiOpen] = useState(true);
  const [voiceAgentLoading, setVoiceAgentLoading] = useState(false);
  const [voiceAgentStarted, setVoiceAgentStarted] = useState(false);
  const [voiceStatus, setVoiceStatus] = useState('Hindi pa naka-start.');

  const roomLink = useMemo(() => {
    const url = new URL(window.location.href);
    url.searchParams.set('room', connection?.roomName || roomName || 'demo-room');
    return url.toString();
  }, [connection, roomName]);

  async function joinRoom(event) {
    event.preventDefault();
    setError('');
    setCopied(false);
    setVoiceAgentStarted(false);
    setVoiceStatus('Hindi pa naka-start.');

    if (!participantName.trim()) {
      setError('Ilagay muna ang pangalan mo.');
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/token`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          room_name: roomName,
          participant_name: participantName,
        }),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || 'Hindi nakagawa ng LiveKit token.');
      }

      const url = new URL(window.location.href);
      url.searchParams.set('room', data.room_name);
      window.history.replaceState({}, '', url);

      setConnection({
        serverUrl: data.server_url,
        token: data.participant_token,
        roomName: data.room_name,
        identity: data.participant_identity,
        displayName: data.participant_name || participantName,
      });
    } catch (err) {
      setError(err.message || 'May error sa pag-join.');
    } finally {
      setLoading(false);
    }
  }

  async function startVoiceAgent() {
    if (!connection || voiceAgentLoading || voiceAgentStarted) {
      return;
    }

    setError('');
    setVoiceAgentLoading(true);
    setVoiceStatus('Nagpapatawag ng Gemini Voice AI sa room...');

    try {
      const response = await fetch(`${API_BASE}/api/dispatch-agent`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          room_name: connection.roomName,
          participant_name: connection.displayName,
        }),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || 'Hindi ma-start ang Gemini Voice AI.');
      }

      setVoiceAgentStarted(true);
      setVoiceStatus(
        data.already_dispatched
          ? `Naka-request na si ${data.agent_name}. Hintayin siyang lumabas sa participants.`
          : `Na-request na si ${data.agent_name}. Magsasalita siya kapag naka-join na.`
      );
    } catch (err) {
      setVoiceStatus('Hindi na-start ang Gemini Voice AI.');
      setError(err.message || 'May error sa pag-start ng Gemini Voice AI.');
    } finally {
      setVoiceAgentLoading(false);
    }
  }

  async function copyInviteLink() {
    try {
      await navigator.clipboard.writeText(roomLink);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch {
      setError('Hindi ma-copy ang link. I-copy mo na lang ang URL sa browser.');
    }
  }

  if (!connection) {
    return (
      <main className="lobbyPage">
        <section className="heroCard">
          <div className="badge">LiveKit Video + Chat + Gemini AI</div>
          <h1>Gemini AI Video Room</h1>
          <p>
            Gumawa o sumali sa room. Parehong room name ang gamitin ng mga kausap mo para magkita kayo sa video call, chat, at pwede mong i-start ang Gemini Voice AI assistant.
          </p>

          <form className="joinForm" onSubmit={joinRoom}>
            <label>
              Pangalan mo
              <input
                value={participantName}
                onChange={(e) => setParticipantName(e.target.value)}
                placeholder="Hal. Alvin"
                autoComplete="name"
              />
            </label>

            <label>
              Room name
              <input
                value={roomName}
                onChange={(e) => setRoomName(e.target.value)}
                placeholder="demo-room"
              />
            </label>

            {error && <div className="errorBox">{error}</div>}

            <button type="submit" disabled={loading}>
              {loading ? 'Kumokonekta...' : 'Join Room'}
            </button>
          </form>

          <div className="tips">
            <strong>Test:</strong> buksan sa dalawang browser/tab, same room name, magkaibang pangalan. Para gumana ang Gemini Voice AI, patakbuhin din ang <code>agent/agent.py</code> service.
          </div>
        </section>
      </main>
    );
  }

  return (
    <main className="roomPage">
      <header className="roomHeader">
        <div>
          <span className="eyebrow">Room</span>
          <h2>{connection.roomName}</h2>
        </div>

        <div className="roomActions">
          <button
            className="voiceButton"
            onClick={startVoiceAgent}
            disabled={voiceAgentLoading || voiceAgentStarted}
            title="Starts the Python LiveKit Gemini voice agent. The agent service must be running."
          >
            {voiceAgentLoading ? 'Starting Gemini Voice...' : voiceAgentStarted ? 'Gemini Voice Requested' : 'Start Gemini Voice'}
          </button>
          <button className="secondaryButton" onClick={() => setAiOpen((value) => !value)}>
            {aiOpen ? 'Hide AI' : 'Show AI'}
          </button>
          <button className="secondaryButton" onClick={copyInviteLink}>
            {copied ? 'Copied!' : 'Copy Invite Link'}
          </button>
          <button className="dangerButton" onClick={() => setConnection(null)}>
            Leave
          </button>
        </div>
      </header>

      {error && <div className="floatingError">{error}</div>}

      <div className="voiceStatusBar">{voiceStatus}</div>

      <div className={`roomShell ${aiOpen ? '' : 'aiClosed'}`}>
        <section className="videoArea" aria-label="LiveKit video conference">
          <LiveKitRoom
            token={connection.token}
            serverUrl={connection.serverUrl}
            connect={true}
            video={true}
            audio={true}
            data-lk-theme="default"
            style={{ height: '100%' }}
            onDisconnected={() => setConnection(null)}
            onError={(err) => setError(err.message)}
          >
            <VideoConference />
          </LiveKitRoom>
        </section>

        {aiOpen && (
          <AIChatPanel
            roomName={connection.roomName}
            participantName={connection.displayName}
            voiceStatus={voiceStatus}
          />
        )}
      </div>
    </main>
  );
}
