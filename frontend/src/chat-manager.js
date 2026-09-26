/**
 * SIA Chat Manager
 * Formats, renders, and manages conversation messages, action cards,
 * and permission confirmations.
 */

class SiaChatManager {
  constructor(containerId) {
    this.container = document.getElementById(containerId);
  }

  appendUserMessage(text) {
    const wrap = document.createElement("div");
    wrap.className = "message-wrapper user-wrapper";
    wrap.innerHTML = `
      <div class="message-sender">Sagar</div>
      <div class="message-bubble user-bubble">${this.escapeHtml(text)}</div>
    `;
    this.container.appendChild(wrap);
    this.scrollToBottom();
  }

  appendAssistantMessage(text, toolResult = null) {
    const wrap = document.createElement("div");
    wrap.className = "message-wrapper assistant-wrapper";

    let html = `
      <div class="message-sender">SIA</div>
      <div class="message-bubble assistant-bubble">
        ${this.formatMarkdown(text)}
    `;

    // Render action card if present
    if (toolResult && toolResult.success && toolResult.data) {
      html += this.renderActionCard(toolResult);
    }

    html += `</div>`;
    wrap.innerHTML = html;
    this.container.appendChild(wrap);
    this.scrollToBottom();
  }

  renderActionCard(toolResult) {
    const data = toolResult.data;

    // 1. YouTube playback card
    if (data.url && data.url.includes("youtube.com")) {
      return `
        <div class="action-card action-youtube">
          <div class="action-card-header">
            <span class="action-card-title">YouTube Automation</span>
            <span class="lead-pill">Playing Live</span>
          </div>
          <div class="action-card-body">
            <div><b>Query:</b> "${this.escapeHtml(data.query || 'Track')}"</div>
            <div style="margin-top:4px;">
              <a href="${data.url}" target="_blank" style="color:var(--cyan);text-decoration:none;">Open in YouTube ↗</a>
            </div>
          </div>
        </div>
      `;
    }

    // 2. DineMotion Website UX Analysis card
    if (data.modern_score !== undefined) {
      const opps = data.opportunities || [];
      return `
        <div class="action-card action-lead">
          <div class="action-card-header">
            <span class="action-card-title">DineMotion Website Audit</span>
            <span class="lead-pill">Score: ${data.modern_score}/100</span>
          </div>
          <div class="action-card-body">
            <div><b>Target:</b> ${this.escapeHtml(data.url)}</div>
            <div style="margin-top:6px;"><b>Identified Opportunities:</b></div>
            <div class="lead-pill-row">
              ${opps.map(o => `<span class="lead-pill">${this.escapeHtml(o)}</span>`).join("")}
            </div>
          </div>
        </div>
      `;
    }

    // 3. Task created card
    if (data.title && data.status) {
      return `
        <div class="action-card">
          <div class="action-card-header">
            <span class="action-card-title">Task Recorded</span>
            <span class="lead-pill">${data.priority || 'medium'} priority</span>
          </div>
          <div class="action-card-body">
            <div>${this.escapeHtml(data.title)}</div>
          </div>
        </div>
      `;
    }

    return "";
  }

  showConfirmationModal(confirmationId, message, toolResult) {
    const modal = document.getElementById("confirmationModal");
    const desc = document.getElementById("confirmDescription");
    const details = document.getElementById("confirmDetails");
    const riskBadge = document.getElementById("confirmRiskBadge");

    if (!modal) return;

    desc.textContent = message;
    riskBadge.textContent = `${toolResult.risk_level || 'MEDIUM'} RISK ACTION`;
    details.textContent = JSON.stringify(toolResult.parameters || {}, null, 2);

    modal.dataset.currentId = confirmationId;
    modal.style.display = "flex";
  }

  async submitMessage(text) {
    if (!text || !text.trim()) return;

    const cleanText = text.trim();
    this.appendUserMessage(cleanText);

    // Clear input field
    const input = document.getElementById("textInput");
    if (input) input.value = "";

    window.siaCore.setState("thinking");
    document.getElementById("coreStatusText").textContent = "Processing...";

    try {
      const resp = await window.siaApi.sendChatMessage(cleanText);
      if (resp) {
        this.handleSiaResponse(resp);
      }
    } catch (e) {
      this.appendAssistantMessage("Sir, I had trouble connecting to the local backend. Please verify that SIA Core is running.");
      window.siaCore.setState("error");
    }
  }

  handleSiaResponse(data) {
    if (data.requires_confirmation) {
      this.showConfirmationModal(data.confirmation_id, data.response_text, data.tool_result || {});
      window.siaCore.setState("warning");
      document.getElementById("coreStatusText").textContent = "Awaiting confirmation, Sir.";
      return;
    }

    this.appendAssistantMessage(data.response_text, data.tool_result);
    document.getElementById("coreStatusText").textContent = "Standing by for instructions, Sir.";

    if (data.audio_base64 && window.siaVoice) {
      window.siaVoice.playAudioResponse(data.audio_base64);
    } else {
      window.siaCore.setState(data.state || "idle");
    }
  }

  scrollToBottom() {
    this.container.scrollTop = this.container.scrollHeight;
  }

  escapeHtml(str) {
    if (!str) return "";
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  formatMarkdown(text) {
    if (!text) return "";
    let safe = this.escapeHtml(text);
    // Bold
    safe = safe.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
    // Newlines
    safe = safe.replace(/\n/g, "<br>");
    return safe;
  }
}

// Global Chat instance
window.siaChat = new SiaChatManager("conversationStream");
