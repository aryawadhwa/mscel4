import React, { useEffect, useRef } from 'react';

const CHARS = ['L', 'O', 'V', 'E', '↑', '→', 'Fair', 'Bias', 'Data', 'Audit', 'AI'];

export default function PretextHero() {
  const canvasRef = useRef(null);
  const containerRef = useRef(null);
  const badges = useRef([]);
  const mouse = useRef({ x: 0, y: 0, active: false });

  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    let animationFrameId;

    const init = () => {
      const w = window.innerWidth;
      const h = 500;
      canvas.width = w * window.devicePixelRatio;
      canvas.height = h * window.devicePixelRatio;
      canvas.style.width = `${w}px`;
      canvas.style.height = `${h}px`;
      ctx.scale(window.devicePixelRatio, window.devicePixelRatio);

      const area = w * h;
      const badgeCount = 200;
      const cellSize = Math.sqrt(area / badgeCount);
      const cols = Math.floor(w / cellSize);
      const rows = Math.floor(h / cellSize);

      badges.current = [];
      for (let r = 0; r < rows; r++) {
        for (let c = 0; c < cols; c++) {
          const jx = (Math.random() - 0.5) * cellSize * 0.8;
          const jy = (Math.random() - 0.5) * cellSize * 0.8;
          badges.current.push({
            x: (c + 0.5) * cellSize + jx,
            y: (r + 0.5) * cellSize + jy,
            originX: (c + 0.5) * cellSize + jx,
            originY: (r + 0.5) * cellSize + jy,
            vx: 0,
            vy: 0,
            driftAngle: Math.random() * Math.PI * 2,
            char: CHARS[Math.floor(Math.random() * CHARS.length)],
            rotation: Math.random() * 0.2 - 0.1,
            color: `hsla(${Math.random() * 40 + 160}, 70%, 80%, 0.6)` // Pastel blue/greens
          });
        }
      }
    };

    const animate = () => {
      const w = canvas.width / window.devicePixelRatio;
      const h = canvas.height / window.devicePixelRatio;
      ctx.clearRect(0, 0, w, h);

      const REPEL_RADIUS = 150;
      const REPEL_STRENGTH = 15;
      const DRIFT = 0.04;
      const DAMPING = 0.95;
      const RETURN_STRENGTH = 0.02;

      badges.current.forEach((badge) => {
        // 1. Repulsion from mouse
        if (mouse.current.active) {
          const dx = badge.x - mouse.current.x;
          const dy = badge.y - mouse.current.y;
          const dist = Math.sqrt(dx * dx + dy * dy);

          if (dist < REPEL_RADIUS && dist > 0) {
            const force = (REPEL_RADIUS - dist) / REPEL_RADIUS * REPEL_STRENGTH;
            badge.vx += (dx / dist) * force;
            badge.vy += (dy / dist) * force;
          }
        }

        // 2. Return to origin (Gravity)
        badge.vx += (badge.originX - badge.x) * RETURN_STRENGTH;
        badge.vy += (badge.originY - badge.y) * RETURN_STRENGTH;

        // 3. Slow random drift
        badge.driftAngle += (Math.random() - 0.5) * 0.05;
        badge.vx += Math.cos(badge.driftAngle) * DRIFT;
        badge.vy += Math.sin(badge.driftAngle) * DRIFT;

        // 4. Update physics
        badge.vx *= DAMPING;
        badge.vy *= DAMPING;
        badge.x += badge.vx;
        badge.y += badge.vy;

        // 5. Render
        const distToMouse = mouse.current.active 
          ? Math.sqrt((badge.x - mouse.current.x)**2 + (badge.y - mouse.current.y)**2)
          : 1000;

        ctx.save();
        ctx.translate(badge.x, badge.y);
        ctx.rotate(badge.rotation);

        if (distToMouse < REPEL_RADIUS * 1.2) {
          ctx.beginPath();
          ctx.fillStyle = badge.color;
          ctx.arc(0, 0, 16, 0, Math.PI * 2);
          ctx.fill();
          ctx.fillStyle = '#0f172a'; // Slate 900
          ctx.font = 'bold 10px Inter';
          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';
          ctx.fillText(badge.char, 0, 0);
        } else {
          ctx.beginPath();
          ctx.strokeStyle = '#e2e8f0'; // Slate 200
          ctx.lineWidth = 1;
          ctx.arc(0, 0, 16, 0, Math.PI * 2);
          ctx.stroke();
          ctx.fillStyle = '#94a3b8'; // Slate 400
          ctx.font = '9px Inter';
          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';
          ctx.fillText(badge.char, 0, 0);
        }
        ctx.restore();
      });

      animationFrameId = requestAnimationFrame(animate);
    };

    init();
    animate();

    const handleMouseMove = (e) => {
      const rect = canvas.getBoundingClientRect();
      mouse.current.x = e.clientX - rect.left;
      mouse.current.y = e.clientY - rect.top;
      mouse.current.active = true;
    };

    const handleMouseLeave = () => {
      mouse.current.active = false;
    };

    window.addEventListener('resize', init);
    canvas.addEventListener('mousemove', handleMouseMove);
    canvas.addEventListener('mouseleave', handleMouseLeave);

    return () => {
      window.removeEventListener('resize', init);
      canvas.removeEventListener('mousemove', handleMouseMove);
      canvas.removeEventListener('mouseleave', handleMouseLeave);
      cancelAnimationFrame(animationFrameId);
    };
  }, []);

  return (
    <div ref={containerRef} className="relative w-full h-[500px] flex items-center justify-center overflow-hidden">
      <canvas ref={canvasRef} className="absolute inset-0 z-0" />
      <div className="relative z-10 text-center pointer-events-none">
        <h1 className="text-[clamp(4rem,15vw,10rem)] font-bold tracking-tighter text-slate-950 leading-none">
          de.bias
        </h1>
        <p className="mt-8 text-lg font-medium text-slate-500 max-w-lg mx-auto leading-relaxed">
          High-performance structural calibration for synthetic credit datasets.
        </p>
      </div>
    </div>
  );
}
