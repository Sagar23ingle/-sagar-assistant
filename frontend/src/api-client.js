class SiaApiClient {
  constructor() {
    this.ws = null;
    this.sessionId = 'default';
    this.listeners = new Map();
    this.connect();
  }

  on(e, cb) {
    if (!this.listeners.has(e)) this.listeners.set(e, []);
    this.listeners.get(e).push(cb);
  }

  emit(e, ...a) {
    for (const cb of this.listeners.get(e) || []) {
      try { cb(...a); } catch (_) {}
    }
  }

  connect() {
    const p = location.protocol === 'https:' ? 'wss' : 'ws';
    this.ws = new WebSocket(`${p}://${location.host}/ws`);
    this.ws.onopen = () => this.emit('connection', true);
    this.ws.onmessage = (e) => {
      try {
        const d = JSON.parse(e.data);
        if (d.type === 'stream_chunk') this.emit('chunk', d.chunk);
        if (d.type === 'stream_end') this.emit('stream_end', d.payload || d);
        if (d.type === 'sia_response') this.emit('response', d.payload);
        if (d.type === 'state_change') this.emit('state', d.state, d.details);
      } catch (err) {
        console.error('WS parse error:', err);
      }
    };
    this.ws.onclose = () => {
      this.emit('connection', false);
      setTimeout(() => this.connect(), 2500);
    };
    this.ws.onerror = (err) => {
      console.warn('WS error:', err);
    };
  }

  async sendChatMessage(text, generate_audio = true) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: 'user_message', text, session_id: this.sessionId, generate_audio }));
      return { streaming: true };
    }
    const r = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text, session_id: this.sessionId, generate_audio })
    });
    return r.json();
  }

  async status() { return fetch('/api/status').then(r => r.json()); }
  async settings() { return fetch('/api/settings').then(r => r.json()); }
  async saveSettings(s) {
    return fetch('/api/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(s)
    }).then(r => r.json());
  }
  async keyStatus() { return fetch('/api/gemini-key').then(r => r.json()); }
  async setKey(api_key) {
    return fetch('/api/gemini-key', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ api_key })
    }).then(r => r.json());
  }
  async tasks() { return fetch('/api/tasks').then(r => r.json()); }
  async memories() { return fetch('/api/memories').then(r => r.json()); }
  async leads() { return fetch('/api/leads').then(r => r.json()); }
  async completeTask(id) { return fetch(`/api/tasks/${id}?status=completed`, { method: 'PATCH' }).then(r => r.json()); }
  async confirmAction(id, approved) {
    return fetch('/api/confirm', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ confirmation_id: id, approved })
    }).then(r => r.json());
  }
  async stopSpeech() {
    try { await fetch('/api/tts/stop', { method: 'POST' }); } catch (_) {}
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: 'interrupt' }));
    }
  }
}

window.siaApi = new SiaApiClient();
