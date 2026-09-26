/**
 * SIA API Client & WebSocket Manager
 * Handles bidirectional real-time communication with the backend.
 */

class SiaApiClient {
  constructor() {
    this.ws = null;
    this.sessionId = "default";
    this.listeners = new Map();
    this.isConnected = false;
    this.initWebSocket();
  }

  initWebSocket() {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host;
    const wsUrl = `${protocol}//${host}/ws`;

    try {
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        this.isConnected = true;
        this.emit("connection_change", { connected: true });
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          this.handleIncomingMessage(data);
        } catch (e) {
          console.error("Failed to parse WebSocket message:", e);
        }
      };

      this.ws.onclose = () => {
        this.isConnected = false;
        this.emit("connection_change", { connected: false });
        // Attempt reconnect after 3 seconds
        setTimeout(() => this.initWebSocket(), 3000);
      };

      this.ws.onerror = (err) => {
        console.warn("WebSocket error:", err);
      };
    } catch (e) {
      console.warn("WebSocket initialization failed:", e);
    }
  }

  handleIncomingMessage(data) {
    if (data.type === "state_change") {
      this.emit("state_change", data.state, data.details);
    } else if (data.type === "sia_response") {
      this.emit("sia_response", data.payload);
    } else if (data.type === "welcome") {
      this.emit("state_change", data.state || "idle");
    }
  }

  on(event, callback) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, []);
    }
    this.listeners.get(event).push(callback);
  }

  emit(event, ...args) {
    if (this.listeners.has(event)) {
      for (const cb of this.listeners.get(event)) {
        try { cb(...args); } catch (e) { console.error(e); }
      }
    }
  }

  async sendChatMessage(text, generateAudio = true) {
    // If WebSocket is open, send via socket for instant streaming
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({
        type: "user_message",
        text: text,
        session_id: this.sessionId,
        generate_audio: generateAudio,
      }));
      return null;
    }

    // Fallback to HTTP POST
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: text,
        session_id: this.sessionId,
        generate_audio: generateAudio,
      }),
    });
    return await res.json();
  }

  async confirmAction(confirmationId, approved) {
    const res = await fetch("/api/confirm", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        confirmation_id: confirmationId,
        approved: approved,
      }),
    });
    return await res.json();
  }

  async fetchTasks(status = null) {
    const url = status ? `/api/tasks?status=${status}` : "/api/tasks";
    const res = await fetch(url);
    return await res.json();
  }

  async completeTask(taskId) {
    const res = await fetch(`/api/tasks/${taskId}?status=completed`, { method: "PATCH" });
    return await res.json();
  }

  async fetchMemories(category = null) {
    const url = category ? `/api/memories?category=${category}` : "/api/memories";
    const res = await fetch(url);
    return await res.json();
  }

  async fetchLeads() {
    const res = await fetch("/api/leads");
    return await res.json();
  }

  async stopSpeech() {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: "interrupt" }));
    }
    await fetch("/api/tts/stop", { method: "POST" });
  }

  async clearHistory() {
    await fetch("/api/history", { method: "DELETE" });
  }
}

// Global API instance
window.siaApi = new SiaApiClient();
