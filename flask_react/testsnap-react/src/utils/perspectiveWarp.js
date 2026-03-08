function clamp(v, min, max) {
  return Math.max(min, Math.min(max, v));
}

function solveLinearSystem(A, b) {
  const n = b.length;
  const M = Array.from({ length: n }, (_, i) => A[i].slice().concat([b[i]]));

  for (let col = 0; col < n; col++) {
    let pivot = col;
    for (let r = col + 1; r < n; r++) {
      if (Math.abs(M[r][col]) > Math.abs(M[pivot][col])) pivot = r;
    }
    if (Math.abs(M[pivot][col]) < 1e-12) return null;
    if (pivot !== col) {
      const tmp = M[col];
      M[col] = M[pivot];
      M[pivot] = tmp;
    }
    const div = M[col][col];
    for (let c = col; c <= n; c++) M[col][c] /= div;
    for (let r = 0; r < n; r++) {
      if (r === col) continue;
      const factor = M[r][col];
      if (!factor) continue;
      for (let c = col; c <= n; c++) {
        M[r][c] -= factor * M[col][c];
      }
    }
  }

  return M.map((row) => row[n]);
}

export function computeHomography(src, dst) {
  const A = [];
  const b = [];
  for (let i = 0; i < 4; i++) {
    const x = src[i].x;
    const y = src[i].y;
    const u = dst[i].x;
    const v = dst[i].y;
    A.push([x, y, 1, 0, 0, 0, -u * x, -u * y]);
    b.push(u);
    A.push([0, 0, 0, x, y, 1, -v * x, -v * y]);
    b.push(v);
  }
  const h = solveLinearSystem(A, b);
  if (!h) return null;
  return [
    [h[0], h[1], h[2]],
    [h[3], h[4], h[5]],
    [h[6], h[7], 1]
  ];
}

export function applyHomography(H, x, y) {
  const denom = H[2][0] * x + H[2][1] * y + H[2][2];
  if (!denom) return { x: 0, y: 0 };
  const nx = (H[0][0] * x + H[0][1] * y + H[0][2]) / denom;
  const ny = (H[1][0] * x + H[1][1] * y + H[1][2]) / denom;
  return { x: nx, y: ny };
}

function bilinearSample(data, sw, sh, x, y) {
  const x0 = Math.floor(x);
  const y0 = Math.floor(y);
  const x1 = clamp(x0 + 1, 0, sw - 1);
  const y1 = clamp(y0 + 1, 0, sh - 1);
  const dx = x - x0;
  const dy = y - y0;

  const idx00 = (y0 * sw + x0) * 4;
  const idx10 = (y0 * sw + x1) * 4;
  const idx01 = (y1 * sw + x0) * 4;
  const idx11 = (y1 * sw + x1) * 4;

  const out = [0, 0, 0, 0];
  for (let c = 0; c < 4; c++) {
    const v00 = data[idx00 + c];
    const v10 = data[idx10 + c];
    const v01 = data[idx01 + c];
    const v11 = data[idx11 + c];
    const v0 = v00 * (1 - dx) + v10 * dx;
    const v1 = v01 * (1 - dx) + v11 * dx;
    out[c] = v0 * (1 - dy) + v1 * dy;
  }
  return out;
}

export async function warpImageToCanvas(imgEl, srcPts, outW, outH) {
  const srcCanvas = document.createElement('canvas');
  srcCanvas.width = imgEl.naturalWidth || imgEl.width;
  srcCanvas.height = imgEl.naturalHeight || imgEl.height;
  const sctx = srcCanvas.getContext('2d', { willReadFrequently: true });
  sctx.drawImage(imgEl, 0, 0);
  const srcImg = sctx.getImageData(0, 0, srcCanvas.width, srcCanvas.height);

  const dstPts = [
    { x: 0, y: 0 },
    { x: outW - 1, y: 0 },
    { x: outW - 1, y: outH - 1 },
    { x: 0, y: outH - 1 }
  ];
  const H = computeHomography(dstPts, srcPts);
  if (!H) throw new Error('透视矩阵计算失败');

  const outCanvas = document.createElement('canvas');
  outCanvas.width = outW;
  outCanvas.height = outH;
  const octx = outCanvas.getContext('2d', { willReadFrequently: true });
  const outImg = octx.createImageData(outW, outH);
  const sw = srcCanvas.width;
  const sh = srcCanvas.height;
  const sdata = srcImg.data;
  const odata = outImg.data;

  for (let y = 0; y < outH; y++) {
    for (let x = 0; x < outW; x++) {
      const p = applyHomography(H, x, y);
      const sx = p.x;
      const sy = p.y;
      const oi = (y * outW + x) * 4;
      if (sx < 0 || sy < 0 || sx >= sw - 1 || sy >= sh - 1) {
        odata[oi + 3] = 0;
        continue;
      }
      const rgba = bilinearSample(sdata, sw, sh, sx, sy);
      odata[oi] = rgba[0];
      odata[oi + 1] = rgba[1];
      odata[oi + 2] = rgba[2];
      odata[oi + 3] = rgba[3];
    }
  }
  octx.putImageData(outImg, 0, 0);
  return outCanvas;
}

export function estimateOutputSize(srcPts) {
  const dist = (a, b) => Math.hypot(a.x - b.x, a.y - b.y);
  const w1 = dist(srcPts[0], srcPts[1]);
  const w2 = dist(srcPts[3], srcPts[2]);
  const h1 = dist(srcPts[0], srcPts[3]);
  const h2 = dist(srcPts[1], srcPts[2]);
  const w = Math.max(240, Math.round((w1 + w2) / 2));
  const h = Math.max(240, Math.round((h1 + h2) / 2));
  return { width: w, height: h };
}

