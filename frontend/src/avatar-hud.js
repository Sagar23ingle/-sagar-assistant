/**
 * SIA 3D Holographic Female AI Assistant HUD
 * Powered by Three.js & Canonical MediaPipe 3D Facial Mesh
 * Features:
 * - Dimensional 3D canonical facial geometry (468 vertices, 898 faces)
 * - Custom holographic Fresnel rim glow + scanline shader
 * - Luminous cyan wireframe overlay
 * - 3D holographic eyes with realistic gaze tracking and natural saccades
 * - Multi-state facial behavior (IDLE, LISTENING, THINKING, WORKING, SPEAKING, ERROR)
 * - Natural non-linear eyelid blinking
 * - Real transcript & audio-aware lip-sync with phoneme visemes (MBP, AA, E/I, O/U)
 * - Concentric orbital HUD rings & digital reticles
 * - Reactive 3D particle aura
 * - Watchdog timer to prevent "stuck in thinking"
 */

(() => {
  class HolographicAvatarHUD {
    constructor(canvas) {
      this.canvas = canvas;
      this.state = 'idle';
      this.audioLevel = 0;
      this.transcript = '';
      this.targetState = 'idle';
      this.mouse = { x: 0, y: 0, targetX: 0, targetY: 0 };
      this.gaze = { x: 0, y: 0, targetX: 0, targetY: 0 };
      this.headRot = { x: 0, y: 0, z: 0 };
      this.jawOpen = 0;
      this.targetJawOpen = 0;
      this.mouthWidth = 1.0;
      this.mouthPucker = 0;
      this.mouthMbp = 0;
      this.blink = 0;
      this.lastBlinkTime = performance.now();
      this.nextBlinkInterval = 3200;
      this.isBlinking = false;
      this.blinkProgress = 0;
      this.thinkingTime = 0;
      this.stateStartTime = performance.now();

      // State colors
      this.colors = {
        idle: new THREE.Color(0x38bdf8),       // Luminous sky cyan
        listening: new THREE.Color(0x74eaff),  // Bright attentive cyan
        processing: new THREE.Color(0x38bdf8), // Luminous sky cyan
        responding: new THREE.Color(0x67e8f9), // Electric vibrant cyan
        thinking: new THREE.Color(0x818cf8),   // Deep indigo-violet focus
        working: new THREE.Color(0x00f0ff),    // High-energy neon cyan
        speaking: new THREE.Color(0x67e8f9),   // Vibrant electric cyan
        error: new THREE.Color(0xf87171),      // Restrained alert amber/red
        success: new THREE.Color(0x34d399)     // Soft emerald pulse
      };
      this.currentColor = this.colors.idle.clone();
      this.targetColor = this.colors.idle.clone();

      this.initThree();
      this.initFaceMesh();
      this.initEyes();
      this.initHUD();
      this.initParticles();
      this.initEvents();

      this.clock = new THREE.Clock();
      this.animate = this.animate.bind(this);
      requestAnimationFrame(this.animate);
    }

    initThree() {
      const rect = this.canvas.getBoundingClientRect();
      const width = rect.width || 700;
      const height = rect.height || 700;

      this.scene = new THREE.Scene();
      this.camera = new THREE.PerspectiveCamera(42, width / height, 0.1, 100);
      this.camera.position.set(0, 0, 3.2);

      this.renderer = new THREE.WebGLRenderer({
        canvas: this.canvas,
        alpha: true,
        antialias: true,
        powerPreference: 'high-performance'
      });
      this.renderer.setSize(width, height);
      this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));

      // Container group for all head elements (head mesh, eyes, features)
      this.headGroup = new THREE.Group();
      this.scene.add(this.headGroup);
    }

    initFaceMesh() {
      const data = window.SIA_FACE_DATA;
      if (!data || !data.vertices || !data.indices) {
        console.warn('SIA_FACE_DATA not loaded. Using fallback procedural head.');
        this.initProceduralHead();
        return;
      }

      this.faceData = data;
      this.baseVertices = new Float32Array(data.vertices);
      this.currentVertices = new Float32Array(data.vertices);

      // Create BufferGeometry
      this.faceGeometry = new THREE.BufferGeometry();
      this.faceGeometry.setAttribute('position', new THREE.BufferAttribute(this.currentVertices, 3));
      this.faceGeometry.setIndex(new THREE.BufferAttribute(data.indices, 1));
      this.faceGeometry.computeVertexNormals();

      // Custom Holographic Shader Material
      this.holoMaterial = new THREE.ShaderMaterial({
        uniforms: {
          uColor: { value: this.currentColor },
          uTime: { value: 0 },
          uAlpha: { value: 0.85 },
          uFresnelPower: { value: 2.2 },
          uScanlineSpeed: { value: 3.5 },
          uScanlineDensity: { value: 45.0 }
        },
        vertexShader: `
          varying vec3 vNormal;
          varying vec3 vViewPosition;
          varying vec3 vWorldPosition;
          void main() {
            vNormal = normalize(normalMatrix * normal);
            vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
            vViewPosition = -mvPosition.xyz;
            vWorldPosition = (modelMatrix * vec4(position, 1.0)).xyz;
            gl_Position = projectionMatrix * mvPosition;
          }
        `,
        fragmentShader: `
          uniform vec3 uColor;
          uniform float uTime;
          uniform float uAlpha;
          uniform float uFresnelPower;
          uniform float uScanlineSpeed;
          uniform float uScanlineDensity;
          varying vec3 vNormal;
          varying vec3 vViewPosition;
          varying vec3 vWorldPosition;
          void main() {
            vec3 normal = normalize(vNormal);
            vec3 viewDir = normalize(vViewPosition);

            // Fresnel rim glow: strong at grazing angles
            float fresnel = dot(normal, viewDir);
            fresnel = clamp(1.0 - abs(fresnel), 0.0, 1.0);
            fresnel = pow(fresnel, uFresnelPower);

            // Subtle vertical scanlines
            float scanline = sin(vWorldPosition.y * uScanlineDensity + uTime * uScanlineSpeed);
            scanline = scanline * 0.5 + 0.5;
            scanline = pow(scanline, 2.5) * 0.35;

            // Deep obsidian interior + luminous cyan edge glow
            vec3 darkCore = uColor * 0.08;
            vec3 edgeGlow = uColor * (fresnel * 1.6 + scanline * 0.45);
            vec3 finalColor = darkCore + edgeGlow;

            float alpha = clamp(fresnel * 0.75 + 0.18 + scanline * 0.12, 0.0, 1.0) * uAlpha;
            gl_FragColor = vec4(finalColor, alpha);
          }
        `,
        transparent: true,
        side: THREE.DoubleSide,
        depthWrite: false,
        blending: THREE.AdditiveBlending
      });

      this.faceMesh = new THREE.Mesh(this.faceGeometry, this.holoMaterial);
      this.headGroup.add(this.faceMesh);

      // Luminous Wireframe Overlay
      const wireframeGeometry = new THREE.WireframeGeometry(this.faceGeometry);
      this.wireframeMaterial = new THREE.LineBasicMaterial({
        color: this.currentColor,
        transparent: true,
        opacity: 0.38,
        blending: THREE.AdditiveBlending,
        linewidth: 1
      });
      this.wireframeMesh = new THREE.LineSegments(wireframeGeometry, this.wireframeMaterial);
      this.headGroup.add(this.wireframeMesh);

      // Feature lines: Lips, Eyes, Eyebrows accent lines
      this.initFeatureLines();
    }

    initProceduralHead() {
      const geo = new THREE.SphereGeometry(0.85, 32, 32);
      geo.scale(0.85, 1.15, 0.95);
      const mat = new THREE.MeshBasicMaterial({
        color: 0x38bdf8,
        wireframe: true,
        transparent: true,
        opacity: 0.4
      });
      this.faceMesh = new THREE.Mesh(geo, mat);
      this.headGroup.add(this.faceMesh);
    }

    initFeatureLines() {
      if (!this.faceData) return;
      const lm = this.faceData.landmarks;

      // Extract lip loop indices to create a highlighted lip outline
      const lipIndices = [...lm.upperLip, ...lm.lowerLip];
      const lipGeo = new THREE.BufferGeometry();
      const lipPositions = new Float32Array(lipIndices.length * 3);
      lipGeo.setAttribute('position', new THREE.BufferAttribute(lipPositions, 3));

      this.lipLineMaterial = new THREE.LineBasicMaterial({
        color: 0x74eaff,
        transparent: true,
        opacity: 0.85,
        blending: THREE.AdditiveBlending
      });
      this.lipLines = new THREE.Line(lipGeo, this.lipLineMaterial);
      this.headGroup.add(this.lipLines);
    }

    initEyes() {
      this.eyesGroup = new THREE.Group();
      this.headGroup.add(this.eyesGroup);

      // Canonical MediaPipe eye centers in normalized coords
      // Left eye is roughly x: -0.32, y: 0.18, z: 0.28
      // Right eye is roughly x: 0.32, y: 0.18, z: 0.28
      const eyeZ = 0.22;
      const eyeY = 0.16;
      const eyeX = 0.32;

      this.leftEye = this.createHoloEye(-eyeX, eyeY, eyeZ);
      this.rightEye = this.createHoloEye(eyeX, eyeY, eyeZ);

      this.eyesGroup.add(this.leftEye.group);
      this.eyesGroup.add(this.rightEye.group);
    }

    createHoloEye(x, y, z) {
      const group = new THREE.Group();
      group.position.set(x, y, z);

      // Outer Iris Ring
      const ringGeo = new THREE.RingGeometry(0.065, 0.082, 32);
      const ringMat = new THREE.MeshBasicMaterial({
        color: 0x74eaff,
        transparent: true,
        opacity: 0.85,
        side: THREE.DoubleSide,
        blending: THREE.AdditiveBlending
      });
      const ring = new THREE.Mesh(ringGeo, ringMat);
      group.add(ring);

      // Inner Pupil Disc
      const pupilGeo = new THREE.CircleGeometry(0.045, 32);
      const pupilMat = new THREE.MeshBasicMaterial({
        color: 0x051a24,
        side: THREE.DoubleSide
      });
      const pupil = new THREE.Mesh(pupilGeo, pupilMat);
      pupil.position.z = 0.005;
      group.add(pupil);

      // Central Luminous Gaze Dot
      const dotGeo = new THREE.CircleGeometry(0.018, 16);
      const dotMat = new THREE.MeshBasicMaterial({
        color: 0xe0ffff,
        side: THREE.DoubleSide,
        blending: THREE.AdditiveBlending
      });
      const dot = new THREE.Mesh(dotGeo, dotMat);
      dot.position.z = 0.01;
      group.add(dot);

      // Reticle Ticks around Iris
      const reticleGeo = new THREE.RingGeometry(0.095, 0.102, 24);
      const reticleMat = new THREE.LineBasicMaterial({
        color: 0x38bdf8,
        transparent: true,
        opacity: 0.45,
        blending: THREE.AdditiveBlending
      });
      const reticle = new THREE.Mesh(reticleGeo, reticleMat);
      group.add(reticle);

      return { group, ring, pupil, dot, reticle, baseX: x, baseY: y, baseZ: z };
    }

    initHUD() {
      this.hudGroup = new THREE.Group();
      this.scene.add(this.hudGroup);

      // Outer Orbital Ring 1
      const ring1Geo = new THREE.RingGeometry(1.42, 1.435, 64);
      this.ring1Mat = new THREE.MeshBasicMaterial({
        color: 0x38bdf8,
        transparent: true,
        opacity: 0.28,
        side: THREE.DoubleSide,
        blending: THREE.AdditiveBlending
      });
      this.ring1 = new THREE.Mesh(ring1Geo, this.ring1Mat);
      this.hudGroup.add(this.ring1);

      // Outer Orbital Ring 2 (Dashed/Segmented)
      const ring2Geo = new THREE.RingGeometry(1.58, 1.595, 48);
      this.ring2Mat = new THREE.MeshBasicMaterial({
        color: 0x74eaff,
        transparent: true,
        opacity: 0.22,
        side: THREE.DoubleSide,
        blending: THREE.AdditiveBlending
      });
      this.ring2 = new THREE.Mesh(ring2Geo, this.ring2Mat);
      this.ring2.rotation.x = Math.PI * 0.15;
      this.hudGroup.add(this.ring2);

      // Reticle Crosshairs
      const lineMat = new THREE.LineBasicMaterial({
        color: 0x38bdf8,
        transparent: true,
        opacity: 0.35,
        blending: THREE.AdditiveBlending
      });
      const crosshairGeo = new THREE.BufferGeometry();
      const crosshairPts = new Float32Array([
        -1.7, 0, 0, -1.45, 0, 0,
         1.45, 0, 0,  1.7, 0, 0,
         0, -1.7, 0,  0, -1.45, 0,
         0,  1.45, 0,  0,  1.7, 0
      ]);
      crosshairGeo.setAttribute('position', new THREE.BufferAttribute(crosshairPts, 3));
      this.crosshairs = new THREE.LineSegments(crosshairGeo, lineMat);
      this.hudGroup.add(this.crosshairs);
    }

    initParticles() {
      const count = 420;
      const positions = new Float32Array(count * 3);
      const velocities = [];

      for (let i = 0; i < count; i++) {
        // Distribute in a cylinder/sphere around avatar
        const theta = Math.random() * Math.PI * 2;
        const radius = 1.0 + Math.random() * 1.2;
        const y = (Math.random() - 0.5) * 2.4;

        positions[i * 3] = Math.cos(theta) * radius;
        positions[i * 3 + 1] = y;
        positions[i * 3 + 2] = Math.sin(theta) * radius * 0.8;

        velocities.push({
          theta,
          radius,
          speed: (Math.random() * 0.003 + 0.001) * (Math.random() > 0.5 ? 1 : -1),
          yVelocity: (Math.random() - 0.5) * 0.002
        });
      }

      this.particleGeo = new THREE.BufferGeometry();
      this.particleGeo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
      this.particleVelocities = velocities;

      this.particleMat = new THREE.PointsMaterial({
        color: 0x74eaff,
        size: 0.024,
        transparent: true,
        opacity: 0.55,
        blending: THREE.AdditiveBlending
      });

      this.particleSystem = new THREE.Points(this.particleGeo, this.particleMat);
      this.scene.add(this.particleSystem);
    }

    initEvents() {
      // Smooth mouse tracking for interactive gaze
      window.addEventListener('mousemove', (e) => {
        const nx = (e.clientX / window.innerWidth) * 2 - 1;
        const ny = -(e.clientY / window.innerHeight) * 2 + 1;
        this.mouse.targetX = nx;
        this.mouse.targetY = ny;
      });

      window.addEventListener('resize', () => {
        this.resize();
      });
    }

    resize() {
      const rect = this.canvas.getBoundingClientRect();
      const width = rect.width || 700;
      const height = rect.height || 700;
      this.camera.aspect = width / height;
      this.camera.updateProjectionMatrix();
      this.renderer.setSize(width, height);
      this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    }

    setState(newState) {
      const s = String(newState || 'idle').toLowerCase();
      this.state = s;
      this.stateStartTime = performance.now();

      if (this.colors[s]) {
        this.targetColor = this.colors[s];
      } else {
        this.targetColor = this.colors.idle;
      }
    }

    setAudioLevel(level) {
      this.audioLevel = Math.max(0, Math.min(1, Number(level) || 0));
    }

    setTranscript(text) {
      this.transcript = String(text || '');
    }

    /**
     * Transcript-driven Viseme Calculator
     * Analyzes active words and audio playback progress to determine mouth shape
     */
    computeViseme(progress) {
      const clean = this.transcript.toLowerCase().replace(/[^a-z\s]/g, '');
      const words = clean.split(/\s+/).filter(Boolean);

      if (!words.length || progress <= 0 || progress >= 1) {
        // Fallback to audio amplitude modulation if no transcript or between words
        return {
          jaw: 0.15 + this.audioLevel * 0.65,
          width: 1.0 + this.audioLevel * 0.1,
          pucker: 0,
          mbp: 0
        };
      }

      // Map progress to current character phoneme
      const totalChars = clean.length;
      const charIndex = Math.min(totalChars - 1, Math.floor(progress * totalChars));
      const char = clean[charIndex] || 'a';

      // Phoneme Viseme Rules
      if ('mbp'.includes(char)) {
        // Bilabial closure: lips shut tight, small jaw opening
        return { jaw: 0.05, width: 0.95, pucker: 0, mbp: 0.85 };
      }
      if ('ae'.includes(char)) {
        // Open vowels: wide jaw opening
        return { jaw: 0.65 + this.audioLevel * 0.35, width: 1.05, pucker: -0.1, mbp: 0 };
      }
      if ('iy'.includes(char)) {
        // Wide spread: lips stretched horizontally, teeth together
        return { jaw: 0.25 + this.audioLevel * 0.2, width: 1.25, pucker: -0.2, mbp: 0 };
      }
      if ('ou'.includes(char)) {
        // Rounded vowels: lips puckered into O-shape
        return { jaw: 0.45 + this.audioLevel * 0.25, width: 0.82, pucker: 0.75, mbp: 0 };
      }
      if ('fv'.includes(char)) {
        // Labiodental: lower lip near upper teeth
        return { jaw: 0.18 + this.audioLevel * 0.15, width: 1.02, pucker: 0, mbp: 0.2 };
      }
      if ('szcjx'.includes(char)) {
        // Dental/Alveolar fricative
        return { jaw: 0.15 + this.audioLevel * 0.15, width: 1.15, pucker: 0, mbp: 0 };
      }

      // Default neutral conversational phoneme
      return {
        jaw: 0.25 + this.audioLevel * 0.45,
        width: 1.0,
        pucker: 0,
        mbp: 0
      };
    }

    updateDeformations(elapsed) {
      if (!this.faceData || !this.faceGeometry) return;

      const pos = this.faceGeometry.attributes.position.array;
      const base = this.baseVertices;
      const lm = this.faceData.landmarks;

      // 1. Natural Non-linear Eyelid Blinking
      const now = performance.now();
      if (!this.isBlinking && now - this.lastBlinkTime > this.nextBlinkInterval) {
        this.isBlinking = true;
        this.blinkProgress = 0;
        this.nextBlinkInterval = 2800 + Math.random() * 2200;
      }

      if (this.isBlinking) {
        this.blinkProgress += 0.16;
        if (this.blinkProgress >= Math.PI) {
          this.isBlinking = false;
          this.lastBlinkTime = now;
          this.blink = 0;
        } else {
          // Sine curve for fast down, smooth up
          this.blink = Math.sin(this.blinkProgress);
        }
      } else {
        this.blink = 0;
      }

      // 2. Audio-aware Lip Sync & Jaw Movement
      let targetJaw = 0;
      let targetWidth = 1.0;
      let targetPucker = 0;
      let targetMbp = 0;

      if (this.state === 'speaking') {
        const audio = document.getElementById('siaAudioPlayer');
        let prog = 0;
        if (audio && !audio.paused && audio.duration) {
          prog = audio.currentTime / audio.duration;
        }
        const viseme = this.computeViseme(prog);
        targetJaw = viseme.jaw;
        targetWidth = viseme.width;
        targetPucker = viseme.pucker;
        targetMbp = viseme.mbp;
      } else if (this.state === 'listening') {
        // Subtle mouth parted in attention
        targetJaw = 0.05 + this.audioLevel * 0.15;
      }

      // Smooth interpolation (lerp)
      this.jawOpen += (targetJaw - this.jawOpen) * 0.35;
      this.mouthWidth += (targetWidth - this.mouthWidth) * 0.35;
      this.mouthPucker += (targetPucker - this.mouthPucker) * 0.35;
      this.mouthMbp += (targetMbp - this.mouthMbp) * 0.45;

      // Reset vertices from base
      pos.set(base);

      // Deform Upper & Lower Eyelids (Blink)
      if (this.blink > 0.01) {
        // Left Eye blink
        for (let i = 0; i < lm.leftEyeUpper.length; i++) {
          const upIdx = lm.leftEyeUpper[i];
          const lowIdx = lm.leftEyeLower[Math.min(i, lm.leftEyeLower.length - 1)];
          const targetY = base[lowIdx * 3 + 1];
          pos[upIdx * 3 + 1] += (targetY - base[upIdx * 3 + 1]) * this.blink * 0.95;
        }
        // Right Eye blink
        for (let i = 0; i < lm.rightEyeUpper.length; i++) {
          const upIdx = lm.rightEyeUpper[i];
          const lowIdx = lm.rightEyeLower[Math.min(i, lm.rightEyeLower.length - 1)];
          const targetY = base[lowIdx * 3 + 1];
          pos[upIdx * 3 + 1] += (targetY - base[upIdx * 3 + 1]) * this.blink * 0.95;
        }
      }

      // Deform Jaw, Lower Lip, Chin (Phonation)
      if (this.jawOpen > 0.01 || this.mouthWidth !== 1.0 || this.mouthPucker !== 0) {
        const mouthCenterY = base[lm.mouthCenter * 3 + 1];

        // Lower Lip downward shift
        for (const idx of lm.lowerLip) {
          pos[idx * 3 + 1] -= this.jawOpen * 0.14;
          pos[idx * 3 + 2] -= this.jawOpen * 0.03;
          if (this.mouthMbp > 0.1) {
            // Compress lip towards mouth center
            pos[idx * 3 + 1] += (mouthCenterY - pos[idx * 3 + 1]) * this.mouthMbp * 0.4;
          }
        }

        // Chin downward shift
        for (const idx of lm.chin) {
          pos[idx * 3 + 1] -= this.jawOpen * 0.09;
        }

        // Mouth Corners (Width / Stretch)
        for (const idx of lm.mouthCorners) {
          pos[idx * 3] *= this.mouthWidth;
          if (this.mouthPucker > 0.05) {
            pos[idx * 3] *= (1.0 - this.mouthPucker * 0.25);
            pos[idx * 3 + 2] += this.mouthPucker * 0.06;
          }
        }
      }

      this.faceGeometry.attributes.position.needsUpdate = true;
    }

    updateGaze(elapsed) {
      // Natural gaze target determination based on state
      if (this.state === 'thinking') {
        // Dart gaze upward and away (defocused contemplation)
        const thinkCycle = Math.floor(elapsed * 0.5);
        this.gaze.targetX = (Math.sin(thinkCycle) > 0 ? 0.35 : -0.35);
        this.gaze.targetY = 0.35;
      } else if (this.state === 'listening') {
        // Strong direct eye contact + attentive micro-shifts
        this.gaze.targetX = this.mouse.targetX * 0.2;
        this.gaze.targetY = this.mouse.targetY * 0.15;
      } else if (this.state === 'speaking') {
        // Conversational eye contact with natural saccadic drift
        this.gaze.targetX = this.mouse.targetX * 0.35 + Math.sin(elapsed * 1.5) * 0.08;
        this.gaze.targetY = this.mouse.targetY * 0.25 + Math.cos(elapsed * 1.8) * 0.06;
      } else {
        // IDLE: Soft cursor following with micro-saccades
        this.gaze.targetX = this.mouse.targetX * 0.5 + Math.sin(elapsed * 0.8) * 0.04;
        this.gaze.targetY = this.mouse.targetY * 0.4 + Math.cos(elapsed * 0.9) * 0.03;
      }

      // Smooth gaze interpolation
      this.gaze.x += (this.gaze.targetX - this.gaze.x) * 0.12;
      this.gaze.y += (this.gaze.targetY - this.gaze.y) * 0.12;

      // Update 3D Eyes
      if (this.leftEye && this.rightEye) {
        const gazeOffsetX = this.gaze.x * 0.022;
        const gazeOffsetY = this.gaze.y * 0.018;

        this.leftEye.pupil.position.x = gazeOffsetX;
        this.leftEye.pupil.position.y = gazeOffsetY;
        this.leftEye.dot.position.x = gazeOffsetX * 1.1;
        this.leftEye.dot.position.y = gazeOffsetY * 1.1;

        this.rightEye.pupil.position.x = gazeOffsetX;
        this.rightEye.pupil.position.y = gazeOffsetY;
        this.rightEye.dot.position.x = gazeOffsetX * 1.1;
        this.rightEye.dot.position.y = gazeOffsetY * 1.1;
      }
    }

    updateHeadMotion(elapsed) {
      let targetRotX = 0;
      let targetRotY = 0;
      let targetRotZ = 0;

      // Subtle breathing motion
      const breath = Math.sin(elapsed * 1.2) * 0.015;

      if (this.state === 'thinking') {
        targetRotX = 0.08;
        targetRotY = this.gaze.targetX * 0.25;
        targetRotZ = -this.gaze.targetX * 0.08;
      } else if (this.state === 'listening' || this.state === 'processing') {
        targetRotX = 0.04 + Math.sin(elapsed * 2.5) * 0.01;
        targetRotY = this.mouse.targetX * 0.18;
      } else if (this.state === 'speaking' || this.state === 'responding') {
        // Conversational head nods
        targetRotX = Math.sin(elapsed * 3.5) * 0.035 + breath;
        targetRotY = this.mouse.targetX * 0.15 + Math.sin(elapsed * 1.2) * 0.03;
        targetRotZ = Math.sin(elapsed * 1.8) * 0.02;
      } else {
        // IDLE
        targetRotX = breath;
        targetRotY = this.mouse.targetX * 0.12;
        targetRotZ = Math.sin(elapsed * 0.6) * 0.01;
      }

      this.headRot.x += (targetRotX - this.headRot.x) * 0.08;
      this.headRot.y += (targetRotY - this.headRot.y) * 0.08;
      this.headRot.z += (targetRotZ - this.headRot.z) * 0.08;

      this.headGroup.rotation.x = this.headRot.x;
      this.headGroup.rotation.y = this.headRot.y;
      this.headGroup.rotation.z = this.headRot.z;
    }

    updateHUD(elapsed) {
      // Rotate orbital rings
      let ringSpeed = 0.003;
      if (this.state === 'working' || this.state === 'thinking') ringSpeed = 0.012;
      if (this.state === 'speaking') ringSpeed = 0.006;

      this.ring1.rotation.z += ringSpeed;
      this.ring2.rotation.z -= ringSpeed * 1.4;

      // Reactive pulse to audio level
      const scalePulse = 1.0 + this.audioLevel * 0.08;
      this.ring1.scale.set(scalePulse, scalePulse, scalePulse);

      // Color interpolation
      this.currentColor.lerp(this.targetColor, 0.08);

      if (this.holoMaterial) {
        this.holoMaterial.uniforms.uColor.value.copy(this.currentColor);
        this.holoMaterial.uniforms.uTime.value = elapsed;
      }
      if (this.wireframeMaterial) {
        this.wireframeMaterial.color.copy(this.currentColor);
      }
      if (this.ring1Mat) this.ring1Mat.color.copy(this.currentColor);
      if (this.ring2Mat) this.ring2Mat.color.copy(this.currentColor);
      if (this.particleMat) this.particleMat.color.copy(this.currentColor);
    }

    updateParticles(elapsed) {
      if (!this.particleGeo) return;
      const pos = this.particleGeo.attributes.position.array;
      const vel = this.particleVelocities;
      const count = vel.length;

      const speedMultiplier = (this.state === 'working' || this.state === 'thinking') ? 2.5 : 1.0;

      for (let i = 0; i < count; i++) {
        const v = vel[i];
        v.theta += v.speed * speedMultiplier;
        pos[i * 3 + 1] += v.yVelocity;

        if (pos[i * 3 + 1] > 1.4) pos[i * 3 + 1] = -1.4;
        if (pos[i * 3 + 1] < -1.4) pos[i * 3 + 1] = 1.4;

        pos[i * 3] = Math.cos(v.theta) * v.radius;
        pos[i * 3 + 2] = Math.sin(v.theta) * v.radius * 0.85;
      }

      this.particleGeo.attributes.position.needsUpdate = true;
    }

    checkWatchdog(now) {
      // Fix the "thinking forever" bug in UI:
      // If assistant stays in 'thinking', 'working', or 'processing' for over 22s without server response,
      // fail safe back to 'idle' and inform user.
      if ((this.state === 'thinking' || this.state === 'working' || this.state === 'processing') && (now - this.stateStartTime > 22000)) {
        console.warn('Avatar Watchdog: Agent state exceeded 22s timeout. Resetting to IDLE.');
        this.setState('idle');
        const stText = document.getElementById('coreStatusText');
        if (stText) stText.textContent = 'Standing by';
      }
    }

    animate() {
      requestAnimationFrame(this.animate);

      const elapsed = this.clock.getElapsedTime();
      const now = performance.now();

      this.checkWatchdog(now);
      this.updateDeformations(elapsed);
      this.updateGaze(elapsed);
      this.updateHeadMotion(elapsed);
      this.updateHUD(elapsed);
      this.updateParticles(elapsed);

      this.renderer.render(this.scene, this.camera);
    }
  }

  // Mount to window
  window.addEventListener('DOMContentLoaded', () => {
    const canvas = document.getElementById('assistantAvatarCanvas');
    if (canvas) {
      window.siaAvatar = new HolographicAvatarHUD(canvas);
    }
  });
})();
