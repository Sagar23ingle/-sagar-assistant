(() => {
class AssistantAvatarHUD {
  constructor(canvas){this.canvas=canvas;this.ctx=canvas.getContext('2d');this.state='idle';this.level=0;this.transcript='';this.t0=performance.now();this.resize();addEventListener('resize',()=>this.resize());requestAnimationFrame(t=>this.render(t));}
  resize(){const r=this.canvas.getBoundingClientRect(),d=Math.min(devicePixelRatio||1,2);this.canvas.width=Math.max(1,Math.floor(r.width*d));this.canvas.height=Math.max(1,Math.floor(r.height*d));this.ctx.setTransform(d,0,0,d,0,0);this.w=r.width;this.h=r.height;}
  setState(s){this.state=s||'idle';}
  setAudioLevel(v){this.level=Math.max(0,Math.min(1,Number(v)||0));}
  setTranscript(t){this.transcript=String(t||'');}
  rgba(hex,a){const n=parseInt(hex.slice(1),16);return `rgba(${n>>16&255},${n>>8&255},${n&255},${a})`;}
  mouthShape(progress){const chars=[...this.transcript.toLowerCase()].filter(c=>/[a-z]/.test(c)); if(!chars.length)return [.18,0]; const c=chars[Math.min(chars.length-1,Math.floor(progress*chars.length))]; if('ae'.includes(c))return [.72,c==='e'?.55:-.05]; if('iy'.includes(c))return [.28,.7]; if('ou'.includes(c))return [.45,c==='u'?-.72:-.5]; if('mbp'.includes(c))return [.02,0]; if('fv'.includes(c))return [.12,.2]; if('szcjx'.includes(c))return [.18,.35]; return [.28,0];}
  glow(ctx,x,y,r,a,col){const g=ctx.createRadialGradient(x,y,r*.1,x,y,r);g.addColorStop(0,this.rgba(col,a));g.addColorStop(1,this.rgba(col,0));ctx.fillStyle=g;ctx.beginPath();ctx.arc(x,y,r,0,Math.PI*2);ctx.fill();}
  eye(ctx,x,y,w,h,gaze,open,col){ctx.save();ctx.translate(x+gaze*w,y);ctx.scale(1,open);ctx.fillStyle=this.rgba(col,.12);ctx.beginPath();ctx.ellipse(0,0,w,h,0,0,Math.PI*2);ctx.fill();ctx.shadowBlur=15;ctx.shadowColor=col;ctx.fillStyle=this.rgba('#dfffff',.95);ctx.beginPath();ctx.arc(0,0,h*.65,0,Math.PI*2);ctx.fill();ctx.restore();}
  render(ts){const c=this.ctx,W=this.w||700,H=this.h||700,cx=W/2,cy=H/2,t=(ts-this.t0),r=Math.min(W,H)*.31;const accent='#74eaff';c.clearRect(0,0,W,H);this.glow(c,cx,cy,r*1.9,.10+(this.level*.15),accent);
    const thinking=this.state==='thinking'||this.state==='working',listening=this.state==='listening';
    c.save();c.translate(cx+Math.sin(t*.001)*r*.025,cy+Math.sin(t*.0007)*3);
    // holographic head silhouette
    const g=c.createLinearGradient(0,-r,0,r);g.addColorStop(0,this.rgba('#1a3442',.97));g.addColorStop(1,this.rgba('#071118',.99));c.fillStyle=g;c.strokeStyle=this.rgba(accent,.72);c.lineWidth=1.5;c.beginPath();c.ellipse(0,0,r*.72,r*.92,0,0,Math.PI*2);c.fill();c.stroke();
    c.save();c.globalAlpha=.11;c.strokeStyle=accent;c.lineWidth=.55;for(let y=-r*.75;y<r*.72;y+=7){c.beginPath();c.moveTo(-r*.63,y);c.lineTo(r*.63,y);c.stroke();}c.restore();
    const gaze=thinking?-.22:(listening?.03:Math.sin(t*.0017)*.04),blink=Math.pow(Math.max(0,Math.sin(t*.0009+.7)),28),open=Math.max(.04,1-blink*.96);this.eye(c,-r*.3,-r*.16,r*.27,r*.085,gaze,open,accent);this.eye(c,r*.3,-r*.16,r*.27,r*.085,gaze,open,accent);
    c.strokeStyle=this.rgba(accent,.7);c.lineWidth=Math.max(1.5,r*.015);c.lineCap='round';for(const s of [-1,1]){c.beginPath();c.moveTo(s*r*.5,-r*.35-(thinking?0:Math.sin(t*.004)*r*.02));c.quadraticCurveTo(s*r*.3,-r*.42-(thinking?-.03:0),s*r*.08,-r*.36);c.stroke();}
    c.strokeStyle=this.rgba(accent,.4);c.lineWidth=1.2;c.beginPath();c.moveTo(0,-r*.08);c.lineTo(r*.04,r*.28);c.quadraticCurveTo(0,r*.34,-r*.08,r*.3);c.stroke();
    const audio=document.getElementById('siaAudioPlayer');let p=0;if(audio&&!audio.paused&&audio.duration)p=audio.currentTime/audio.duration;const [op,wide]=this.state==='speaking'?this.mouthShape(p):[.12+this.level*.35,0];const mw=r*(.18+.06*wide),mh=Math.max(1.5,r*.035+op*r*.11);c.fillStyle=this.rgba('#010507',1);c.strokeStyle=this.rgba(accent,.86);c.lineWidth=1.2;c.beginPath();c.ellipse(0,r*.48,mw,mh,0,0,Math.PI*2);c.fill();c.stroke();if(op>.25){c.strokeStyle=this.rgba('#eaffff',.55);c.lineWidth=.8;c.beginPath();c.moveTo(-mw*.65,r*.45);c.quadraticCurveTo(0,r*.48,mw*.65,r*.45);c.stroke();}
    c.strokeStyle=this.rgba(accent,.28);c.lineWidth=1;for(let i=0;i<20;i++){const a=t*.00025+i*Math.PI*2/20,rr=r*(1.08+.01*Math.sin(t*.002+i)),len=i%4===0?10:5;c.beginPath();c.moveTo(Math.cos(a)*rr,Math.sin(a)*rr);c.lineTo(Math.cos(a)*(rr+len),Math.sin(a)*(rr+len));c.stroke();}
    c.restore();c.font='600 10px Inter,system-ui';c.textAlign='center';c.fillStyle=this.rgba(accent,.72);c.fillText(this.state.toUpperCase(),W/2,H-14);requestAnimationFrame(q=>this.render(q));}
}
window.siaAvatar=new AssistantAvatarHUD(document.getElementById('assistantAvatarCanvas'));
})();
