document.addEventListener('DOMContentLoaded', async () => {
  const $ = id => document.getElementById(id);
  const input = $('textInput');

  // Input & Send Handlers
  function send() {
    const text = input.value.trim();
    if (text) {
      window.siaChat.submitMessage(text);
      input.value = '';
    }
  }

  $('btnSendText').onclick = send;
  input.onkeydown = (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      send();
    }
  };

  // Voice Interaction Handlers
  $('btnVoiceInput').onclick = () => window.siaVoice.toggleListening();
  $('btnStopSpeech').onclick = () => window.siaVoice.interrupt();

  // Spacebar Push-to-Talk & Escape Interrupt
  addEventListener('keydown', (e) => {
    if (e.code === 'Space' && document.activeElement !== input && !e.repeat) {
      e.preventDefault();
      window.siaVoice.startListening();
    }
    if (e.key === 'Escape') {
      window.siaVoice.interrupt();
      $('settingsModal').style.display = 'none';
      $('confirmationModal').style.display = 'none';
      $('sideDrawer').classList.remove('open');
    }
  });

  addEventListener('keyup', (e) => {
    if (e.code === 'Space' && document.activeElement !== input) {
      e.preventDefault();
      window.siaVoice.stopListening();
    }
  });

  // State Updates from Backend
  window.siaApi.on('state', (state) => {
    window.siaAvatar?.setState(state);
    const upper = String(state).toUpperCase();
    $('statusLabel').textContent = upper;
    $('systemStatusBadge').className = 'status ' + state;
    const stText = $('coreStatusText');
    if (stText) {
      if (state === 'speaking') stText.textContent = 'Speaking…';
      else if (state === 'thinking') stText.textContent = 'Thinking…';
      else if (state === 'working') stText.textContent = 'Executing workflow…';
      else if (state === 'listening') stText.textContent = 'Listening…';
      else if (state === 'processing') stText.textContent = 'Processing…';
      else if (state === 'responding') stText.textContent = 'Responding…';
      else if (state === 'error') stText.textContent = 'Alert';
      else stText.textContent = 'Standing by';
    }
  });

  window.siaApi.on('chunk', (chunk) => {
    window.siaChat.appendChunk(chunk);
  });

  window.siaApi.on('stream_end', (payload) => {
    window.siaChat.finishStreaming(payload);
  });

  window.siaApi.on('response', (payload) => {
    window.siaChat.handleSiaResponse(payload);
  });

  // Load Settings & Status
  async function loadInitialData() {
    try {
      const [st, set, key] = await Promise.all([
        window.siaApi.status(),
        window.siaApi.settings(),
        window.siaApi.keyStatus()
      ]);

      $('assistantName').textContent = st.assistant_name || 'SIA';
      $('settingAssistantName').value = set.assistant?.name || 'SIA';
      $('settingUserName').value = set.user?.name || 'Sagar';
      $('settingProvider').value = set.ai?.provider || 'hybrid';
      $('settingGeminiModel').value = set.ai?.gemini_model || 'gemini-3.8-flash';
      $('settingOllamaModel').value = set.ai?.ollama_model || 'llama3.2';
      $('settingVoice').value = set.ai?.gemini_voice || 'Aoede';

      $('geminiStatusText').textContent = key.configured
        ? '✓ Gemini API key configured.'
        : '○ No Gemini key configured. SIA will use local Ollama.';
    } catch (err) {
      console.warn('Error loading initial data:', err);
    }
  }
  loadInitialData();

  // Drawer Tabs & Content
  const drawer = $('sideDrawer');
  $('btnDrawer').onclick = async () => {
    drawer.classList.add('open');
    await loadDrawerData();
  };
  $('btnCloseDrawer').onclick = () => drawer.classList.remove('open');

  function switchTab(activeBtnId, activeContentId) {
    ['tabBtnMemories', 'tabBtnTasks', 'tabBtnLeads'].forEach(id => $(id)?.classList.remove('active'));
    ['tabContentMemories', 'tabContentTasks', 'tabContentLeads'].forEach(id => $(id)?.classList.remove('active'));
    $(activeBtnId)?.classList.add('active');
    $(activeContentId)?.classList.add('active');
  }

  $('tabBtnMemories').onclick = () => switchTab('tabBtnMemories', 'tabContentMemories');
  $('tabBtnTasks').onclick = () => switchTab('tabBtnTasks', 'tabContentTasks');
  $('tabBtnLeads').onclick = () => switchTab('tabBtnLeads', 'tabContentLeads');

  $('btnRefreshTasks').onclick = () => loadDrawerData();
  $('btnRefreshLeads').onclick = () => loadDrawerData();

  async function loadDrawerData() {
    try {
      const [mems, tsks, lds] = await Promise.all([
        window.siaApi.memories(),
        window.siaApi.tasks(),
        window.siaApi.leads()
      ]);

      // Render Memories
      $('memoryCountBadge').textContent = mems.length;
      $('drawerMemoriesList').innerHTML = mems.length
        ? mems.map(x => `
          <div class="memory-card">
            <div class="card-tag">${window.siaChat.escape(x.category || 'general')}</div>
            <b>${window.siaChat.escape(x.key)}</b>
            <span>${window.siaChat.escape(x.value)}</span>
          </div>`).join('')
        : '<div class="empty">No memories saved yet. SIA learns preferences as you converse.</div>';

      // Render Tasks
      $('drawerTasksList').innerHTML = tsks.length
        ? tsks.map(x => `
          <div class="task-card">
            <div>
              <b>${window.siaChat.escape(x.title)}</b>
              <div class="sub-text">${window.siaChat.escape(x.description || '')}</div>
            </div>
            <button class="text-btn" onclick="completeTask(${x.id})">Mark Done</button>
          </div>`).join('')
        : '<div class="empty">No pending tasks.</div>';

      // Render Leads & CRM
      $('drawerLeadsList').innerHTML = lds.length
        ? lds.map(x => `
          <div class="lead-card">
            <div class="lead-header">
              <b>${window.siaChat.escape(x.company_name)}</b>
              <span class="score-badge">${x.qualification_score ? 'Score: ' + x.qualification_score : 'Lead'}</span>
            </div>
            <div class="lead-meta">
              ${x.industry ? `<span>${window.siaChat.escape(x.industry)}</span> · ` : ''}
              ${x.location ? `<span>${window.siaChat.escape(x.location)}</span> · ` : ''}
              ${x.website ? `<a href="${x.website.startsWith('http') ? x.website : 'https://' + x.website}" target="_blank">${window.siaChat.escape(x.website)}</a>` : '<span class="warning-text">No Website</span>'}
            </div>
            ${x.qualification_notes ? `<div class="sub-text notes">${window.siaChat.escape(x.qualification_notes)}</div>` : ''}
          </div>`).join('')
        : '<div class="empty">No leads captured yet. Ask SIA: "Find US detailing businesses" or "Discover web design leads".</div>';
    } catch (e) {
      console.warn('Error loading drawer data:', e);
    }
  }

  window.completeTask = async (id) => {
    await window.siaApi.completeTask(id);
    await loadDrawerData();
  };

  // Settings Modal Handlers
  $('btnSettings').onclick = () => $('settingsModal').style.display = 'flex';
  $('btnCloseSettings').onclick = () => $('settingsModal').style.display = 'none';

  $('btnSaveSettings').onclick = async () => {
    try {
      const s = await window.siaApi.settings();
      if (!s.assistant) s.assistant = {};
      if (!s.user) s.user = {};
      if (!s.ai) s.ai = {};
      if (!s.voice) s.voice = {};

      s.assistant.name = $('settingAssistantName').value.trim() || 'SIA';
      s.user.name = $('settingUserName').value.trim() || 'Sagar';
      s.ai.provider = $('settingProvider').value;
      s.ai.gemini_model = $('settingGeminiModel').value.trim() || 'gemini-3.8-flash';
      s.ai.ollama_model = $('settingOllamaModel').value.trim() || 'llama3.2';
      s.ai.gemini_voice = $('settingVoice').value;
      s.voice.engine = s.ai.provider === 'local' ? 'edge-tts' : 'gemini';

      await window.siaApi.saveSettings(s);

      const key = $('settingGeminiKey').value.trim();
      if (key) {
        await window.siaApi.setKey(key);
      }

      $('assistantName').textContent = s.assistant.name;
      $('settingsModal').style.display = 'none';
      $('coreStatusText').textContent = 'Settings saved';
      window.siaAvatar?.setState('success');
      setTimeout(() => window.siaAvatar?.setState('idle'), 1000);
    } catch (err) {
      console.error('Save settings error:', err);
      alert('Failed to save settings');
    }
  };

  // Test Voice Button
  $('btnTestVoice').onclick = async () => {
    try {
      const userName = $('settingUserName').value || 'Sir';
      const r = await fetch('/api/tts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: `Hello ${userName}. I am SIA, your holographic personal assistant. All systems are operational.`,
          language: 'en'
        })
      });
      const d = await r.json();
      if (d.audio_base64 && window.siaVoice) {
        window.siaVoice.playAudioResponse(d.audio_base64, d.mime_type || 'audio/wav');
      }
    } catch (err) {
      console.error('Test voice error:', err);
    }
  };

  // Confirmation Modal Handlers
  $('btnApproveConfirm').onclick = async () => {
    const m = $('confirmationModal');
    const id = m.dataset.currentId;
    m.style.display = 'none';
    try {
      const r = await window.siaApi.confirmAction(id, true);
      if (r.tool_result) {
        window.siaChat.appendAssistantMessage(r.tool_result.message || 'Action executed successfully.', r.tool_result);
      }
    } catch (err) {
      window.siaChat.appendAssistantMessage('Action execution failed or expired.');
    }
    window.siaAvatar?.setState('idle');
  };

  $('btnRejectConfirm').onclick = async () => {
    const m = $('confirmationModal');
    const id = m.dataset.currentId;
    m.style.display = 'none';
    try {
      await window.siaApi.confirmAction(id, false);
      window.siaChat.appendAssistantMessage('Understood, Sir. I cancelled that action.');
    } catch (err) {}
    window.siaAvatar?.setState('idle');
  };
});
