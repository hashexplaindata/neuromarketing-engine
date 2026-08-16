import React, { useState, useEffect } from 'react';

interface ScanpathPlayerProps {
  totalSteps: number;
  currentStep: number;
  onStepChange: (step: number) => void;
}

export const ScanpathPlayer: React.FC<ScanpathPlayerProps> = ({
  totalSteps = 8,
  currentStep,
  onStepChange
}) => {
  const [isPlaying, setIsPlaying] = useState(false);

  useEffect(() => {
    let timer: any;
    if (isPlaying) {
      timer = setInterval(() => {
        const nextStep = currentStep >= totalSteps ? totalSteps : currentStep + 1;
        if (nextStep >= totalSteps) {
          setIsPlaying(false);
        }
        onStepChange(nextStep);
      }, 650);
    }
    return () => clearInterval(timer);
  }, [isPlaying, totalSteps, onStepChange]);

  const togglePlay = () => {
    if (currentStep >= totalSteps) {
      onStepChange(1);
      setIsPlaying(true);
    } else {
      setIsPlaying(!isPlaying);
    }
  };

  return (
    <div className="glass-card">
      <div className="card-title">
        <span>👁️</span> 500ms Saccadic Sequence Playback
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '12px' }}>
        <button
          onClick={togglePlay}
          style={{
            width: '36px',
            height: '36px',
            borderRadius: '50%',
            background: 'var(--accent-cyan)',
            border: 'none',
            color: '#000',
            cursor: 'pointer',
            fontWeight: 800,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '14px'
          }}
        >
          {isPlaying ? '⏸' : '▶'}
        </button>
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
            <span>Fixation Step</span>
            <strong>{currentStep} / {totalSteps}</strong>
          </div>
          <input
            type="range"
            min={1}
            max={totalSteps}
            value={currentStep}
            onChange={(e) => {
              setIsPlaying(false);
              onStepChange(Number(e.target.value));
            }}
            style={{ width: '100%', marginTop: '6px' }}
          />
        </div>
      </div>
      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
        Simulates involuntary macro-saccadic eye movement order governed by Spatial Inhibition of Return (IOR).
      </div>
    </div>
  );
};