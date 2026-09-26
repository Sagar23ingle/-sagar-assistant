/**
 * SIA Voice Controller
 * Coordinates Speech Recognition (STT), Wake-Word detection,
 * Web Audio Analysis, and Neural TTS playback.
 */

class SiaVoiceController {
  constructor() {
    this.recognition = null;
    this.audioPlayer = document.getElementById("siaAudioPlayer");
    this.isListening = false;
    this.wakeWord = "hey sia";
    this.audioContext = null;
    this.analyser = null;
    this.micStream = null;

    this.initSpeechRecognition();
    this.initAudioAnalyser();
  }

  initSpeechRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      console.warn("Browser SpeechRecognition not supported. Push-to-talk available via text.");
      return;
    }

    this.recognition = new SpeechRecognition();
    this.recognition.continuous = true;
    this.recognition.interimResults = true;
    this.recognition.lang = "en-IN"; // Supports Indian English, code-switches to Hindi

    this.recognition.onstart = () => {
      this.isListening = true;
      window.siaCore.setState("listening");
      document.getElementById("btnVoiceInput")?.classList.add("listening");
      this.showTranscriptPreview("Listening...");
    };

    this.recognition.onresult = (event) => {
      let interim = "";
      let final = "";

      for (let i = event.resultIndex; i < event.results.length; ++i) {
        const transcript = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          final += transcript;
        } else {
          interim += transcript;
        }
      }

      const display = final || interim;
      if (display) {
        this.showTranscriptPreview(`"${display.trim()}"`);
      }

      if (final) {
        const clean = final.trim();
        // Check for wake word trigger or direct phrase
        if (clean.toLowerCase().includes(this.wakeWord)) {
          const stripped = clean.replace(/hey sia/i, "").trim();
          if (stripped) {
            this.handleUserVoiceSubmission(stripped);
          }
        } else {
          this.handleUserVoiceSubmission(clean);
        }
      }
    };

    this.recognition.onerror = (event) => {
      console.warn("Speech recognition error:", event.error);
      this.stopListening();
    };

    this.recognition.onend = () => {
      this.isListening = false;
      document.getElementById("btnVoiceInput")?.classList.remove("listening");
      this.hideTranscriptPreview();
      if (window.siaCore.state === "listening") {
        window.siaCore.setState("idle");
      }
    };
  }

  initAudioAnalyser() {
    try {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (!AudioCtx || !this.audioPlayer) return;

      this.audioPlayer.addEventListener("play", () => {
        if (!this.audioContext) {
          this.audioContext = new AudioCtx();
          const source = this.audioContext.createMediaElementSource(this.audioPlayer);
          this.analyser = this.audioContext.createAnalyser();
          this.analyser.fftSize = 64;
          source.connect(this.analyser);
          this.analyser.connect(this.audioContext.destination);
          this.startAudioLoop();
        }
      });
    } catch (e) {
      console.warn("Audio analyser initialization notice:", e);
    }
  }

  startAudioLoop() {
    const buffer = new Uint8Array(this.analyser.frequencyBinCount);
    const checkAudio = () => {
      if (!this.audioPlayer.paused) {
        this.analyser.getByteFrequencyData(buffer);
        let sum = 0;
        for (let i = 0; i < buffer.length; i++) sum += buffer[i];
        const avg = sum / buffer.length;
        window.siaCore.setAudioLevel(Math.min(1.0, avg / 128));
        requestAnimationFrame(checkAudio);
      } else {
        window.siaCore.setAudioLevel(0);
      }
    };
    checkAudio();
  }

  toggleListening() {
    if (this.isListening) {
      this.stopListening();
    } else {
      this.startListening();
    }
  }

  startListening() {
    if (this.recognition && !this.isListening) {
      try {
        this.recognition.start();
      } catch (e) {
        console.warn("Recognition already active:", e);
      }
    }
  }

  stopListening() {
    if (this.recognition && this.isListening) {
      try {
        this.recognition.stop();
      } catch (e) {}
    }
    this.isListening = false;
    document.getElementById("btnVoiceInput")?.classList.remove("listening");
    this.hideTranscriptPreview();
  }

  showTranscriptPreview(text) {
    const el = document.getElementById("liveTranscriptPreview");
    if (el) {
      el.style.display = "block";
      el.textContent = text;
    }
  }

  hideTranscriptPreview() {
    const el = document.getElementById("liveTranscriptPreview");
    if (el) el.style.display = "none";
  }

  handleUserVoiceSubmission(text) {
    this.stopListening();
    if (window.siaChat) {
      window.siaChat.submitMessage(text);
    }
  }

  playAudioResponse(base64Data) {
    if (!this.audioPlayer || !base64Data) return;

    this.audioPlayer.src = `data:audio/mp3;base64,${base64Data}`;
    this.audioPlayer.play().then(() => {
      window.siaCore.setState("speaking");
      document.getElementById("btnStopSpeech").style.display = "flex";
      document.getElementById("btnSendText").style.display = "none";
    }).catch(e => {
      console.warn("Audio playback notice:", e);
    });

    this.audioPlayer.onended = () => {
      window.siaCore.setState("idle");
      document.getElementById("btnStopSpeech").style.display = "none";
      document.getElementById("btnSendText").style.display = "flex";
    };
  }

  interrupt() {
    if (this.audioPlayer) {
      this.audioPlayer.pause();
      this.audioPlayer.currentTime = 0;
    }
    window.siaCore.setState("idle");
    window.siaCore.setAudioLevel(0);
    document.getElementById("btnStopSpeech").style.display = "none";
    document.getElementById("btnSendText").style.display = "flex";
    window.siaApi.stopSpeech();
  }
}

// Global Voice Controller instance
window.siaVoice = new SiaVoiceController();
