import React, { useState, useRef, useCallback } from 'react';

interface ComparisonSliderProps {
  originalImage: string;
  variantImage: string;
  variantLabel: string;
  liftPct?: number;
}

export const ComparisonSlider: React.FC<ComparisonSliderProps> = ({
  originalImage,
  variantImage,
  variantLabel,
  liftPct = 34.2
}) => {
  const [sliderPos, setSliderPos] = useState(50);
  const containerRef = useRef<HTMLDivElement | null>(null);

  const handleMove = useCallback((clientX: number) => {
    if (!containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const x = clientX - rect.left;
    const pos = Math.max(0, Math.min(100, (x / rect.width) * 100));
    setSliderPos(pos);
  }, []);

  const handleTouchMove = (e: React.TouchEvent) => {
    handleMove(e.touches[0].clientX);
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (e.buttons === 1) {
      handleMove(e.clientX);
    }
  };

  return (
    <div
      ref={containerRef}
      onMouseMove={handleMouseMove}
      onTouchMove={handleTouchMove}
      style={{
        position: 'relative',
        width: '100%',
        height: '420px',
        borderRadius: '12px',
        overflow: 'hidden',
        cursor: 'ew-resize',
        userSelect: 'none',
        border: '1px solid rgba(255, 255, 255, 0.1)'
      }}
    >
      {/* Winning Variant (Underneath / Left) */}
      <img
        src={variantImage}
        alt="Optimized Variant"
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '100%',
          height: '100%',
          objectFit: 'cover'
        }}
      />
      <div
        style={{
          position: 'absolute',
          top: 14,
          left: 14,
          background: 'rgba(0, 255, 136, 0.2)',
          border: '1px solid #00ff88',
          color: '#00ff88',
          padding: '4px 10px',
          borderRadius: '6px',
          fontSize: '0.75rem',
          fontWeight: 700,
          backdropFilter: 'blur(8px)',
          zIndex: 10
        }}
      >
        OPTIMIZED: {variantLabel} (+{liftPct}% Expected Lift)
      </div>

      {/* Baseline Image (Clipped / Right) */}
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '100%',
          height: '100%',
          clipPath: `polygon(${sliderPos}% 0, 100% 0, 100% 100%, ${sliderPos}% 100%)`
        }}
      >
        <img
          src={originalImage}
          alt="Baseline Thumbnail"
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'cover'
          }}
        />
        <div
          style={{
            position: 'absolute',
            top: 14,
            right: 14,
            background: 'rgba(255, 255, 255, 0.1)',
            border: '1px solid rgba(255, 255, 255, 0.3)',
            color: '#f0f4f8',
            padding: '4px 10px',
            borderRadius: '6px',
            fontSize: '0.75rem',
            fontWeight: 700,
            backdropFilter: 'blur(8px)'
          }}
        >
          BASELINE
        </div>
      </div>

      {/* Divider Bar */}
      <div
        style={{
          position: 'absolute',
          top: 0,
          bottom: 0,
          left: `${sliderPos}%`,
          width: '3px',
          background: '#00f0ff',
          boxShadow: '0 0 12px #00f0ff',
          zIndex: 20
        }}
      >
        <div
          style={{
            position: 'absolute',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            width: '32px',
            height: '32px',
            borderRadius: '50%',
            background: '#00f0ff',
            boxShadow: '0 0 16px rgba(0, 240, 255, 0.8)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#000',
            fontWeight: 800,
            fontSize: '12px'
          }}
        >
          ◀▶
        </div>
      </div>
    </div>
  );
};