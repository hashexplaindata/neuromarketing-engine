import React, { useRef, useEffect } from 'react';

interface CanvasViewerProps {
  imageSrc: string;
  heatmapSrc?: string;
  focusMapSrc?: string;
  viewMode: 'original' | 'heatmap' | 'focus' | 'scanpath';
  heatmapOpacity: number;
  scanpath: Array<{ step: number; x: number; y: number; duration_ms: number }>;
  gazeVectors: Array<{ center: [number, number]; dx: number; dy: number }>;
  currentStep: number;
}

export const CanvasViewer: React.FC<CanvasViewerProps> = ({
  imageSrc,
  heatmapSrc,
  focusMapSrc,
  viewMode,
  heatmapOpacity,
  scanpath,
  gazeVectors,
  currentStep
}) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const baseImg = new Image();
    baseImg.src = (viewMode === 'focus' && focusMapSrc) ? focusMapSrc : imageSrc;

    baseImg.onload = () => {
      canvas.width = baseImg.naturalWidth || 800;
      canvas.height = baseImg.naturalHeight || 450;
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      // 1. Draw Base Image
      ctx.drawImage(baseImg, 0, 0, canvas.width, canvas.height);

      // 2. Draw Heatmap Overlay if active
      if (viewMode === 'heatmap' && heatmapSrc) {
        const hmImg = new Image();
        hmImg.src = heatmapSrc;
        hmImg.onload = () => {
          ctx.globalAlpha = heatmapOpacity;
          ctx.drawImage(hmImg, 0, 0, canvas.width, canvas.height);
          ctx.globalAlpha = 1.0;
          drawOverlays(ctx);
        };
      } else {
        drawOverlays(ctx);
      }
    };

    const drawOverlays = (ctx: CanvasRenderingContext2D) => {
      // 3. Draw 3D Gaze Vectors
      if (gazeVectors && gazeVectors.length > 0) {
        gazeVectors.forEach((gv) => {
          const [cx, cy] = gv.center;
          const rayLen = 140;
          const endX = cx + gv.dx * rayLen;
          const endY = cy + gv.dy * rayLen;

          ctx.strokeStyle = '#00f0ff';
          ctx.lineWidth = 4;
          ctx.beginPath();
          ctx.moveTo(cx, cy);
          ctx.lineTo(endX, endY);
          ctx.stroke();

          ctx.fillStyle = '#00f0ff';
          ctx.beginPath();
          ctx.arc(endX, endY, 6, 0, Math.PI * 2);
          ctx.fill();
        });
      }

      // 4. Draw Animated Scanpath Saccades
      if (viewMode === 'scanpath' || currentStep > 0) {
        const activePoints = scanpath.slice(0, currentStep);

        // Draw Saccade Lines
        for (let i = 0; i < activePoints.length - 1; i++) {
          const p1 = activePoints[i];
          const p2 = activePoints[i + 1];
          ctx.strokeStyle = 'rgba(255, 230, 0, 0.85)';
          ctx.lineWidth = 3;
          ctx.beginPath();
          ctx.moveTo(p1.x, p1.y);
          ctx.lineTo(p2.x, p2.y);
          ctx.stroke();
        }

        // Draw Fixation Nodes
        activePoints.forEach((pt) => {
          ctx.fillStyle = 'rgba(255, 51, 102, 0.9)';
          ctx.strokeStyle = '#ffffff';
          ctx.lineWidth = 2.5;
          ctx.beginPath();
          ctx.arc(pt.x, pt.y, 20, 0, Math.PI * 2);
          ctx.fill();
          ctx.stroke();

          ctx.fillStyle = '#ffffff';
          ctx.font = 'bold 13px Outfit, sans-serif';
          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';
          ctx.fillText(pt.step.toString(), pt.x, pt.y);
        });
      }
    };
  }, [imageSrc, heatmapSrc, focusMapSrc, viewMode, heatmapOpacity, scanpath, gazeVectors, currentStep]);

  return (
    <div style={{ position: 'relative', maxWidth: '100%', maxHeight: '75vh', borderRadius: '12px', overflow: 'hidden', boxShadow: '0 20px 50px rgba(0,0,0,0.6)' }}>
      <canvas ref={canvasRef} style={{ width: '100%', height: 'auto', display: 'block' }} />
    </div>
  );
};