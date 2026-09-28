class SiaChatManager {
  constructor() {
    this.panel = document.getElementById('transcriptPanel');
    this.watchdogTimer = null;
    this.activeStreamingElement = null;
    this.activeTextSpan = null;
    this.activeText = '';
  }

  escape(s) {
    const d = document.createElement('div');
    d.textContent = s ?? '';
    return d.innerHTML;
  }

  appendUserMessage(text) {
    const el = document.createElement('div');
    el.className = 'transcript-line user';
    el.innerHTML = `<span class="speaker">YOU</span><span>${this.escape(text)}</span>`;
    this.panel.appendChild(el);
    this.panel.scrollTop = this.panel.scrollHeight;
  }

  appendAssistantMessage(text, tool) {
    const el = document.createElement('div');
    el.className = 'transcript-line assistant';
    let extra = '';
    if (tool?.success && tool?.data) {
      extra = `<div class="tool-chip">✓ ${this.escape(tool.message || 'Action executed')}</div>`;
    } else if (tool && !tool.success) {
      extra = `<div class="tool-chip error">⚠ ${this.escape(tool.message || 'Action failed')}</div>`;
    }
    el.innerHTML = `<span class="speaker">SIA</span><span>${this.escape(text)}</span>${extra}`;
    this.panel.appendChild(el);
    this.panel.scrollTop = this.panel.scrollHeight;
  }

  appendChunk(chunk) {
    if (!this.activeStreamingElement) {
      const el = document.createElement('div');
      el.className = 'transcript-line assistant';
      el.innerHTML = `<span class="speaker">SIA</span><span class="response-text"></span><span class="transcript-cursor"></span>`;
      this.panel.appendChild(el);
      this.activeStreamingElement = el;
      this.activeTextSpan = el.querySelector('.response-text');
      this.activeText = '';
    }

    this.activeText += chunk;
    if (this.activeTextSpan) {
      this.activeTextSpan.textContent = this.activeText;
    }
    this.panel.scrollTop = this.panel.scrollHeight;

    window.siaAvatar?.setState('responding');
    const stText = document.getElementById('coreStatusText');
    if (stText) stText.textContent = 'Responding…';
  }

  finishStreaming(data) {
    clearTimeout(this.watchdogTimer);

    if (this.activeStreamingElement) {
      const cursor = this.activeStreamingElement.querySelector('.transcript-cursor');
      if (cursor) cursor.remove();

      if (data?.response_text) {
        if (this.activeTextSpan) this.activeTextSpan.textContent = data.response_text;
      }

      if (data?.tool_result) {
        const tool = data.tool_result;
        let extra = '';
        if (tool.success && tool.data) {
          extra = `<div class="tool-chip">✓ ${this.escape(tool.message || 'Action executed')}</div>`;
        } else if (!tool.success) {
          extra = `<div class="tool-chip error">⚠ ${this.escape(tool.message || 'Action failed')}</div>`;
        }
        if (extra) {
          const chipDiv = document.createElement('div');
          chipDiv.innerHTML = extra;
          this.activeStreamingElement.appendChild(chipDiv.firstElementChild);
        }
      }

      this.activeStreamingElement = null;
      this.activeTextSpan = null;
      this.activeText = '';
    } else if (data?.response_text) {
      this.appendAssistantMessage(data.response_text, data.tool_result);
    }

    if (data?.requires_confirmation) {
      this.showConfirmation(data);
      window.siaAvatar?.setState('thinking');
      const stText = document.getElementById('coreStatusText');
      if (stText) stText.textContent = 'Awaiting permission…';
      return;
    }

    if (data?.response_text) {
      window.siaAvatar?.setTranscript?.(data.response_text);
    }

    const stText = document.getElementById('coreStatusText');
    if (data?.audio_base64 && window.siaVoice) {
      window.siaAvatar?.setState('speaking');
      if (stText) stText.textContent = 'Speaking…';
      window.siaVoice.playAudioResponse(data.audio_base64, data.mime_type || 'audio/wav');
    } else {
      window.siaAvatar?.setState(data?.state || 'idle');
      if (stText) stText.textContent = 'Standing by';
    }
  }

  async submitMessage(text) {
    const clean = (text || '').trim();
    if (!clean) return;

    this.appendUserMessage(clean);
    const input = document.getElementById('textInput');
    if (input) input.value = '';

    // Fast state transition: set to PROCESSING (never thinking for normal input)
    window.siaAvatar?.setState('processing');
    const stText = document.getElementById('coreStatusText');
    if (stText) stText.textContent = 'Processing…';

    // Watchdog fallback: reset state to idle if request hangs for >25s
    clearTimeout(this.watchdogTimer);
    this.watchdogTimer = setTimeout(() => {
      console.warn('ChatManager: Request watchdog fired.');
      if (this.activeStreamingElement) {
        const cursor = this.activeStreamingElement.querySelector('.transcript-cursor');
        if (cursor) cursor.remove();
        this.activeStreamingElement = null;
        this.activeTextSpan = null;
      }
      window.siaAvatar?.setState('idle');
      if (stText) stText.textContent = 'Standing by';
    }, 25000);

    try {
      const res = await window.siaApi.sendChatMessage(clean, true);
      if (res && !res.streaming) {
        clearTimeout(this.watchdogTimer);
        this.handleSiaResponse(res);
      }
    } catch (e) {
      clearTimeout(this.watchdogTimer);
      console.error('Chat error:', e);
      if (this.activeStreamingElement) {
        const cursor = this.activeStreamingElement.querySelector('.transcript-cursor');
        if (cursor) cursor.remove();
        this.activeStreamingElement = null;
        this.activeTextSpan = null;
      }
      this.appendAssistantMessage('Sir, I encountered an issue reaching the local assistant core.');
      window.siaAvatar?.setState('idle');
      if (stText) stText.textContent = 'Standing by';
    }
  }

  handleSiaResponse(data) {
    clearTimeout(this.watchdogTimer);

    if (this.activeStreamingElement) {
      this.finishStreaming(data);
      return;
    }

    if (data.requires_confirmation) {
      this.showConfirmation(data);
      window.siaAvatar?.setState('thinking');
      const stText = document.getElementById('coreStatusText');
      if (stText) stText.textContent = 'Awaiting permission…';
      return;
    }

    this.appendAssistantMessage(data.response_text, data.tool_result);
    window.siaAvatar?.setTranscript?.(data.response_text);

    const stText = document.getElementById('coreStatusText');
    if (data.audio_base64 && window.siaVoice) {
      window.siaAvatar?.setState('speaking');
      if (stText) stText.textContent = 'Speaking…';
      window.siaVoice.playAudioResponse(data.audio_base64, data.mime_type || 'audio/wav');
    } else {
      window.siaAvatar?.setState(data.state || 'idle');
      if (stText) stText.textContent = 'Standing by';
    }
  }

  showConfirmation(data) {
    const m = document.getElementById('confirmationModal');
    if (!m) return;
    m.dataset.currentId = data.confirmation_id;
    document.getElementById('confirmDescription').textContent = data.response_text;
    document.getElementById('confirmDetails').textContent = JSON.stringify(data.tool_result?.parameters || {}, null, 2);
    document.getElementById('confirmRiskBadge').textContent = (data.tool_result?.risk_level || 'MEDIUM') + ' RISK';
    m.style.display = 'flex';
  }
}

window.siaChat = new SiaChatManager();
