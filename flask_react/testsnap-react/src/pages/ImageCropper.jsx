import React, { useEffect, useMemo, useRef, useState } from 'react';
import { estimateOutputSize, warpImageToCanvas } from '../utils/perspectiveWarp';
import './fileProcessing.css';

function clamp(v, min, max) {
  return Math.max(min, Math.min(max, v));
}

function makeDefaultPoints(w, h) {
  const pad = Math.round(Math.min(w, h) * 0.06);
  return [
    { x: pad, y: pad },
    { x: w - pad, y: pad },
    { x: w - pad, y: h - pad },
    { x: pad, y: h - pad }
  ];
}

function distance(a, b) {
  return Math.hypot(a.x - b.x, a.y - b.y);
}

export default function ImageCropper({ file, onCancel, onConfirm }) {
  const containerRef = useRef(null);
  const canvasRef = useRef(null);
  const imgRef = useRef(null);
  const dragRef = useRef({ active: false, idx: -1 });

  const [imgUrl, setImgUrl] = useState('');
  const [imgSize, setImgSize] = useState({ w: 0, h: 0 });
  const [view, setView] = useState({ x: 0, y: 0, w: 0, h: 0, scale: 1 });
  const [points, setPoints] = useState([]);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');

  useEffect(() => {
    if (!file) return () => void 0;
    const url = URL.createObjectURL(file);
    setImgUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  useEffect(() => {
    if (!imgUrl) return;
    const img = new Image();
    imgRef.current = img;
    img.onload = () => {
      const w = img.naturalWidth || img.width || 0;
      const h = img.naturalHeight || img.height || 0;
      setImgSize({ w, h });
      setPoints(makeDefaultPoints(w, h));
    };
    img.onerror = () => setErr('图片加载失败');
    img.src = imgUrl;
  }, [imgUrl]);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return () => void 0;
    const ro = new ResizeObserver(() => {
      const rect = el.getBoundingClientRect();
      const w = rect.width;
      const h = rect.height;
      if (!imgSize.w || !imgSize.h || !w || !h) return;
      const scale = Math.min(w / imgSize.w, h / imgSize.h);
      const drawW = imgSize.w * scale;
      const drawH = imgSize.h * scale;
      const x = Math.round((w - drawW) / 2);
      const y = Math.round((h - drawH) / 2);
      setView({ x, y, w: drawW, h: drawH, scale });
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, [imgSize.w, imgSize.h]);

  const toCanvas = (p) => ({
    x: view.x + p.x * view.scale,
    y: view.y + p.y * view.scale
  });

  const toImage = (x, y) => ({
    x: clamp((x - view.x) / view.scale, 0, imgSize.w),
    y: clamp((y - view.y) / view.scale, 0, imgSize.h)
  });

  const draw = () => {
    const canvas = canvasRef.current;
    const el = containerRef.current;
    const img = imgRef.current;
    if (!canvas || !el || !img || !imgSize.w || !imgSize.h) return;
    const rect = el.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    canvas.width = Math.round(rect.width * dpr);
    canvas.height = Math.round(rect.height * dpr);
    canvas.style.width = `${rect.width}px`;
    canvas.style.height = `${rect.height}px`;
    const ctx = canvas.getContext('2d');
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, rect.width, rect.height);

    ctx.drawImage(img, view.x, view.y, view.w, view.h);

    if (!points || points.length !== 4) return;
    const c0 = toCanvas(points[0]);
    const c1 = toCanvas(points[1]);
    const c2 = toCanvas(points[2]);
    const c3 = toCanvas(points[3]);

    ctx.save();
    ctx.fillStyle = 'rgba(0,0,0,0.45)';
    ctx.beginPath();
    ctx.rect(0, 0, rect.width, rect.height);
    ctx.moveTo(c0.x, c0.y);
    ctx.lineTo(c1.x, c1.y);
    ctx.lineTo(c2.x, c2.y);
    ctx.lineTo(c3.x, c3.y);
    ctx.closePath();
    ctx.fill('evenodd');

    ctx.strokeStyle = 'rgba(190, 200, 255, 0.95)';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(c0.x, c0.y);
    ctx.lineTo(c1.x, c1.y);
    ctx.lineTo(c2.x, c2.y);
    ctx.lineTo(c3.x, c3.y);
    ctx.closePath();
    ctx.stroke();

    const r = 10;
    const handle = (c) => {
      ctx.fillStyle = 'rgba(109,124,255,0.95)';
      ctx.beginPath();
      ctx.arc(c.x, c.y, r, 0, Math.PI * 2);
      ctx.fill();
      ctx.strokeStyle = 'rgba(255,255,255,0.9)';
      ctx.lineWidth = 2;
      ctx.stroke();
    };
    handle(c0);
    handle(c1);
    handle(c2);
    handle(c3);
    ctx.restore();
  };

  useEffect(() => {
    draw();
  }, [imgSize.w, imgSize.h, view.x, view.y, view.w, view.h, view.scale, points]);

  const hitTest = (x, y) => {
    if (!points || points.length !== 4) return -1;
    const pt = { x, y };
    let best = -1;
    let bestDist = 1e9;
    for (let i = 0; i < 4; i++) {
      const c = toCanvas(points[i]);
      const d = distance(pt, c);
      if (d < bestDist) {
        bestDist = d;
        best = i;
      }
    }
    return bestDist <= 22 ? best : -1;
  };

  const onPointerDown = (e) => {
    if (busy) return;
    const canvas = canvasRef.current;
    if (!canvas) return;
    canvas.setPointerCapture?.(e.pointerId);
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    const idx = hitTest(x, y);
    if (idx < 0) return;
    dragRef.current = { active: true, idx };
  };

  const onPointerMove = (e) => {
    if (!dragRef.current.active || busy) return;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    const p = toImage(x, y);
    setPoints((prev) => {
      const next = prev.map((q) => ({ ...q }));
      next[dragRef.current.idx] = p;
      return next;
    });
  };

  const onPointerUp = (e) => {
    const canvas = canvasRef.current;
    canvas?.releasePointerCapture?.(e.pointerId);
    dragRef.current = { active: false, idx: -1 };
  };

  const outputHint = useMemo(() => {
    if (!points || points.length !== 4) return '';
    const sz = estimateOutputSize(points);
    return `${sz.width} × ${sz.height}`;
  }, [points]);

  const confirm = async () => {
    if (busy) return;
    setErr('');
    setBusy(true);
    try {
      const img = imgRef.current;
      if (!img) throw new Error('图片未就绪');
      const sz = estimateOutputSize(points);
      const outCanvas = await warpImageToCanvas(img, points, sz.width, sz.height);
      const blob = await new Promise((resolve) => outCanvas.toBlob(resolve, 'image/png', 0.92));
      if (!blob) throw new Error('生成图片失败');
      const base = String(file?.name || 'image').replace(/\.[^.]+$/, '');
      const outFile = new File([blob], `${base}_cropped.png`, { type: 'image/png' });
      onConfirm?.(outFile);
    } catch (e) {
      setErr(String(e?.message || e || '裁剪失败'));
      setBusy(false);
    }
  };

  return (
    <div className="fpCropMask" role="dialog" aria-modal="true">
      <div className="fpCropPanel">
        <div className="fpCropHeader">
          <div className="fpCropTitle">图片裁剪与透视矫正</div>
          <div className="fpCropMeta">输出尺寸：{outputHint || '—'}</div>
        </div>
        <div ref={containerRef} className="fpCropCanvasWrap">
          <canvas
            ref={canvasRef}
            className="fpCropCanvas"
            onPointerDown={onPointerDown}
            onPointerMove={onPointerMove}
            onPointerUp={onPointerUp}
            onPointerCancel={onPointerUp}
          />
        </div>
        {!!err && <div className="fpCropError">{err}</div>}
        <div className="fpCropActions">
          <button type="button" className="fpBtn fpBtnGhost" onClick={onCancel} disabled={busy}>
            取消
          </button>
          <button type="button" className="fpBtn fpBtnPrimary" onClick={confirm} disabled={busy || !imgUrl}>
            {busy ? '处理中…' : '确认裁剪'}
          </button>
        </div>
      </div>
    </div>
  );
}

