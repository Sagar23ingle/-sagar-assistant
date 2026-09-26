/**
 * SIA Core Visualizer
 * Renders an original, living AI presence with concentric geometric orbits,
 * pulsing core, and audio-reactive circular waveform.
 */

class SiaCoreVisualizer {
  constructor(canvasId) {
    this.canvas = document.getElementById(canvasId);
    this.ctx = this.canvas.getContext("2d");
    this.state = "idle"; // idle, listening, thinking, speaking, working, success, error
    this.angle = 0;
    this.pulse = 0;
    this.audioLevel = 0; // 0.0 to 1.0 from microphone or TTS analyser
    this.particles = [];

    this.initParticles();
    this.startAnimation();
  }

  initParticles() {
    this.particles = [];
    for (let i = 0; i < 28; i++) {
      this.particles.push({
        angle: Math.random() * Math.PI * 2,
        radius: 40 + Math.random() * 70,
        speed: 0.003 + Math.random() * 0.008,
        size: 1.2 + Math.random() * 1.5,
        alpha: 0.2 + Math.random() * 0.6,
      });
    }
  }

  setState(newState) {
    this.state = newState;
    const wrapper = document.querySelector(".core-wrapper");
    if (wrapper) {
      wrapper.className = `core-wrapper state-${newState}`;
    }
  }

  setAudioLevel(level) {
    // Smooth audio transitions
    this.audioLevel = this.audioLevel * 0.6 + level * 0.4;
  }

  startAnimation() {
    const render = () => {
      this.draw();
      requestAnimationFrame(render);
    };
    requestAnimationFrame(render);
  }

  draw() {
    const width = this.canvas.width;
    const height = this.canvas.height;
    const cx = width / 2;
    const cy = height / 2;
    const ctx = this.ctx;

    ctx.clearRect(0, 0, width, height);

    this.angle += (this.state === "thinking" ? 0.035 : 0.008);
    this.pulse += (this.state === "speaking" ? 0.08 : 0.03);

    // Color definitions based on state
    let primaryColor = "rgba(0, 217, 255, ";
    let secondaryColor = "rgba(97, 124, 255, ";

    if (this.state === "thinking") {
      primaryColor = "rgba(97, 124, 255, ";
      secondaryColor = "rgba(0, 217, 255, ";
    } else if (this.state === "working") {
      primaryColor = "rgba(255, 176, 32, ";
      secondaryColor = "rgba(0, 217, 255, ";
    } else if (this.state === "error") {
      primaryColor = "rgba(255, 77, 109, ";
      secondaryColor = "rgba(255, 176, 32, ";
    } else if (this.state === "success") {
      primaryColor = "rgba(0, 229, 138, ";
      secondaryColor = "rgba(0, 217, 255, ";
    }

    const reactiveScale = 1 + (this.audioLevel * 0.35) + Math.sin(this.pulse) * 0.04;

    // 1. Central Ambient Glow
    const bgGrad = ctx.createRadialGradient(cx, cy, 10, cx, cy, 110 * reactiveScale);
    bgGrad.addColorStop(0, primaryColor + (this.state === "idle" ? "0.18)" : "0.32)"));
    bgGrad.addColorStop(0.5, secondaryColor + "0.08)");
    bgGrad.addColorStop(1, "transparent");
    ctx.fillStyle = bgGrad;
    ctx.beginPath();
    ctx.arc(cx, cy, 110 * reactiveScale, 0, Math.PI * 2);
    ctx.fill();

    // 2. Subtle Orbit Particles
    ctx.fillStyle = primaryColor + "0.6)";
    for (const p of this.particles) {
      p.angle += p.speed;
      const px = cx + Math.cos(p.angle) * p.radius * reactiveScale;
      const py = cy + Math.sin(p.angle) * p.radius * reactiveScale;
      ctx.beginPath();
      ctx.arc(px, py, p.size, 0, Math.PI * 2);
      ctx.fill();
    }

    // 3. Inner Geometric Rings
    this.drawGeometricRings(ctx, cx, cy, primaryColor, secondaryColor, reactiveScale);

    // 4. Audio-reactive Circular Waveform
    this.drawCircularWaveform(ctx, cx, cy, primaryColor, reactiveScale);

    // 5. Central Nucleus Core
    const coreRadius = (26 + (this.audioLevel * 14) + Math.sin(this.pulse) * 2.5) * (this.state === "listening" ? 1.25 : 1);
    const coreGrad = ctx.createRadialGradient(cx, cy, 2, cx, cy, coreRadius);
    coreGrad.addColorStop(0, "#ffffff");
    coreGrad.addColorStop(0.3, primaryColor + "0.95)");
    coreGrad.addColorStop(0.8, secondaryColor + "0.5)");
    coreGrad.addColorStop(1, "transparent");

    ctx.fillStyle = coreGrad;
    ctx.beginPath();
    ctx.arc(cx, cy, coreRadius, 0, Math.PI * 2);
    ctx.fill();
  }

  drawGeometricRings(ctx, cx, cy, primary, secondary, scale) {
    // Outer dashed arc
    ctx.save();
    ctx.translate(cx, cy);
    ctx.rotate(this.angle);

    ctx.strokeStyle = primary + "0.3)";
    ctx.lineWidth = 1.5;
    ctx.setLineDash([12, 18, 4, 18]);
    ctx.beginPath();
    ctx.arc(0, 0, 95 * scale, 0, Math.PI * 2);
    ctx.stroke();

    // Secondary counter-rotating ring
    ctx.rotate(-this.angle * 1.8);
    ctx.strokeStyle = secondary + "0.22)";
    ctx.lineWidth = 1;
    ctx.setLineDash([20, 10, 6, 10]);
    ctx.beginPath();
    ctx.arc(0, 0, 72 * scale, 0, Math.PI * 2);
    ctx.stroke();

    ctx.restore();
  }

  drawCircularWaveform(ctx, cx, cy, color, scale) {
    const numPoints = 64;
    const baseRadius = 52 * scale;
    ctx.save();
    ctx.translate(cx, cy);

    ctx.strokeStyle = color + (this.state === "idle" ? "0.5)" : "0.9)");
    ctx.lineWidth = 2;
    ctx.beginPath();

    for (let i = 0; i <= numPoints; i++) {
      const theta = (i / numPoints) * Math.PI * 2;
      // Amplitude reacts to audio level and state
      const wave = Math.sin(theta * 6 + this.pulse * 2) * (this.audioLevel * 18 + 2.5);
      const r = baseRadius + wave;
      const x = Math.cos(theta) * r;
      const y = Math.sin(theta) * r;

      if (i === 0) {
        ctx.moveTo(x, y);
      } else {
        ctx.lineTo(x, y);
      }
    }

    ctx.closePath();
    ctx.stroke();
    ctx.restore();
  }
}

// Global Core instance
window.siaCore = new SiaCoreVisualizer("siaCoreCanvas");
