// src/components/CentralStation/SharedVideo.tsx
import React, { useEffect, useRef } from 'react';

// Browsers share one resource between <img> tags with the same MJPEG URL and animate only one
// of them, so each URL is loaded once and painted into a canvas in every tile that shows it.
const sources = new Map<string, { img: HTMLImageElement; users: number }>();

function acquire(url: string): HTMLImageElement {
  let source = sources.get(url);
  if (!source) {
    const img = new Image();
    img.className = 'shared-video-source';
    img.alt = '';
    img.src = url;
    document.body.appendChild(img);
    source = { img, users: 0 };
    sources.set(url, source);
  }
  source.users += 1;
  return source.img;
}

function release(url: string): void {
  const source = sources.get(url);
  if (!source) return;
  source.users -= 1;
  if (source.users === 0) {
    source.img.src = ''; // closes the MJPEG connection
    source.img.remove();
    sources.delete(url);
  }
}

const FRAME_MS = 66;

const SharedVideo: React.FC<{ url: string; label: string }> = ({ url, label }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const img = acquire(url);
    let raf = 0;
    let last = 0;
    const draw = (now: number) => {
      raf = requestAnimationFrame(draw);
      const canvas = canvasRef.current;
      if (!canvas || !img.naturalWidth || now - last < FRAME_MS) return;
      last = now;
      if (canvas.width !== img.naturalWidth || canvas.height !== img.naturalHeight) {
        canvas.width = img.naturalWidth;
        canvas.height = img.naturalHeight;
      }
      try {
        canvas.getContext('2d')?.drawImage(img, 0, 0);
      } catch {
        // stream between frames or broken; try again next tick
      }
    };
    raf = requestAnimationFrame(draw);
    return () => {
      cancelAnimationFrame(raf);
      release(url);
    };
  }, [url]);

  return <canvas ref={canvasRef} role="img" aria-label={label} />;
};

export default SharedVideo;
