/**
 * SIA Main Application Controller
 * Wires DOM events, keyboard shortcuts, modals, and real-time state.
 */

document.addEventListener("DOMContentLoaded", () => {
  const textInput = document.getElementById("textInput");
  const btnSendText = document.getElementById("btnSendText");
  const btnVoiceInput = document.getElementById("btnVoiceInput");
  const btnStopSpeech = document.getElementById("btnStopSpeech");
  const btnContext = document.getElementById("btnContext");
  const btnTasks = document.getElementById("btnTasks");
  const btnLeads = document.getElementById("btnLeads");
  const btnSettings = document.getElementById("btnSettings");
  const btnCloseDrawer = document.getElementById("btnCloseDrawer");
  const btnCloseSettings = document.getElementById("btnCloseSettings");
  const contextDrawer = document.getElementById("contextDrawer");
  const settingsModal = document.getElementById("settingsModal");
  const confirmationModal = document.getElementById("confirmationModal");
  const btnApproveConfirm = document.getElementById("btnApproveConfirm");
  const btnRejectConfirm = document.getElementById("btnRejectConfirm");
  const btnRefreshTasks = document.getElementById("btnRefreshTasks");
  const btnRefreshMemories = document.getElementById("btnRefreshMemories");
  const btnSaveSettings = document.getElementById("btnSaveSettings");
  const btnTestVoice = document.getElementById("btnTestVoice");
  const btnClearHistoryBtn = document.getElementById("btnClearHistoryBtn");

  // ==================== SEND CHAT ====================

  function sendCurrentInput() {
    const text = textInput.value;
    if (text && text.trim()) {
      window.siaChat.submitMessage(text);
    }
  }

  btnSendText?.addEventListener("click", sendCurrentInput);

  textInput?.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendCurrentInput();
    }
  });

  // ==================== VOICE & KEYBOARD SHORTCUTS ====================

  btnVoiceInput?.addEventListener("click", () => {
    window.siaVoice.toggleListening();
  });

  btnStopSpeech?.addEventListener("click", () => {
    window.siaVoice.interrupt();
  });

  // Push-to-Talk via Spacebar when not typing in an input
  window.addEventListener("keydown", (e) => {
    if (e.code === "Space" && document.activeElement !== textInput && !e.repeat) {
      e.preventDefault();
      window.siaVoice.startListening();
    }
    if (e.key === "Escape") {
      window.siaVoice.interrupt();
      contextDrawer?.classList.remove("open");
      settingsModal.style.display = "none";
      confirmationModal.style.display = "none";
    }
  });

  window.addEventListener("keyup", (e) => {
    if (e.code === "Space" && document.activeElement !== textInput) {
      e.preventDefault();
      window.siaVoice.stopListening();
    }
  });

  // ==================== WEBSOCKET STATE LISTENER ====================

  window.siaApi.on("state_change", (state, details) => {
    window.siaCore.setState(state);
    const label = document.getElementById("statusLabel");
    const badge = document.getElementById("systemStatusBadge");

    if (label && badge) {
      label.textContent = state.toUpperCase();
      badge.className = `status-badge ${state}`;
    }
  });

  window.siaApi.on("sia_response", (payload) => {
    window.siaChat.handleSiaResponse(payload);
  });

  // ==================== CONTEXT DRAWER ====================

  btnContext?.addEventListener("click", () => {
    contextDrawer.classList.toggle("open");
    if (contextDrawer.classList.contains("open")) {
      loadDrawerData();
    }
  });

  btnTasks?.addEventListener("click", () => {
    contextDrawer.classList.add("open");
    loadDrawerData();
  });

  btnLeads?.addEventListener("click", () => {
    window.siaChat.submitMessage("Sia, Nagpur ke restaurants dhund DineMotion ke liye.");
  });

  btnCloseDrawer?.addEventListener("click", () => {
    contextDrawer.classList.remove("open");
  });

  async function loadDrawerData() {
    // 1. Tasks
    const tasks = await window.siaApi.fetchTasks();
    const tasksContainer = document.getElementById("drawerTasksList");
    if (tasks && tasks.length > 0) {
      tasksContainer.innerHTML = tasks.map(t => `
        <div class="task-item-card ${t.status === 'completed' ? 'completed' : ''}">
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <strong>${window.siaChat.escapeHtml(t.title)}</strong>
            ${t.status !== 'completed' ? `<button class="text-btn" onclick="completeTask(${t.id})">✓ Done</button>` : `<span class="lead-pill">Completed</span>`}
          </div>
          ${t.description ? `<div style="color:var(--text-muted);margin-top:2px;">${window.siaChat.escapeHtml(t.description)}</div>` : ''}
        </div>
      `).join("");
    } else {
      tasksContainer.innerHTML = `<div class="empty-state">No pending tasks, Sir.</div>`;
    }

    // 2. Memories
    const memories = await window.siaApi.fetchMemories();
    const memContainer = document.getElementById("drawerMemoriesList");
    if (memories && memories.length > 0) {
      memContainer.innerHTML = memories.map(m => `
        <div class="memory-item-card">
          <div style="color:var(--cyan);font-weight:600;">[${window.siaChat.escapeHtml(m.category.toUpperCase())}] ${window.siaChat.escapeHtml(m.key)}</div>
          <div style="margin-top:3px;color:var(--text);">${window.siaChat.escapeHtml(m.value)}</div>
        </div>
      `).join("");
    } else {
      memContainer.innerHTML = `<div class="empty-state">No stored memories found.</div>`;
    }
  }

  window.completeTask = async (taskId) => {
    await window.siaApi.completeTask(taskId);
    loadDrawerData();
  };

  btnRefreshTasks?.addEventListener("click", loadDrawerData);
  btnRefreshMemories?.addEventListener("click", loadDrawerData);

  // ==================== CONFIRMATION ACTIONS ====================

  btnApproveConfirm?.addEventListener("click", async () => {
    const cid = confirmationModal.dataset.currentId;
    if (cid) {
      confirmationModal.style.display = "none";
      window.siaCore.setState("working");
      document.getElementById("coreStatusText").textContent = "Executing approved action, Sir...";
      const res = await window.siaApi.confirmAction(cid, true);
      if (res && res.tool_result) {
        window.siaChat.appendAssistantMessage(res.tool_result.message || "Action executed successfully, Sir.", res.tool_result);
      }
      window.siaCore.setState("idle");
      document.getElementById("coreStatusText").textContent = "Standing by for instructions, Sir.";
    }
  });

  btnRejectConfirm?.addEventListener("click", async () => {
    const cid = confirmationModal.dataset.currentId;
    if (cid) {
      confirmationModal.style.display = "none";
      await window.siaApi.confirmAction(cid, false);
      window.siaChat.appendAssistantMessage("Understood, Sir. I cancelled that action.");
      window.siaCore.setState("idle");
    }
  });

  // ==================== SETTINGS MODAL ====================

  btnSettings?.addEventListener("click", () => {
    settingsModal.style.display = "flex";
  });

  btnCloseSettings?.addEventListener("click", () => {
    settingsModal.style.display = "none";
  });

  btnTestVoice?.addEventListener("click", async () => {
    const lang = document.getElementById("settingVoiceLang")?.value || "en";
    const res = await fetch("/api/tts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: "Hello Sir. My neural voice is working perfectly and ready for our work.", language: lang }),
    });
    const data = await res.json();
    if (data.audio_base64) {
      window.siaVoice.playAudioResponse(data.audio_base64);
    }
  });

  btnClearHistoryBtn?.addEventListener("click", async () => {
    if (confirm("Sir, are you sure you want to clear our current conversation history?")) {
      await window.siaApi.clearHistory();
      document.getElementById("conversationStream").innerHTML = `
        <div class="message-wrapper assistant-wrapper">
          <div class="message-sender">SIA</div>
          <div class="message-bubble assistant-bubble">History cleared, Sir. Standing by.</div>
        </div>
      `;
    }
  });
});
