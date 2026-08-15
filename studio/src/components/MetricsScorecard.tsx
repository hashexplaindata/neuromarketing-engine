import React from 'react';

interface MetricsScorecardProps {
  predictedCtr?: number;
  expectedRange?: [number, number];
  percentileTier?: string;
  faaScore?: number;
  thetaMemoryScore?: number;
  mobileLegibility?: string;
  ffaDispersion?: number;
}

export const MetricsScorecard: React.FC<MetricsScorecardProps> = ({
  predictedCtr = 8.64,
  expectedRange = [7.89, 9.39],
  percentileTier = 'Top 15% (High Performer)',
  faaScore = 0.42,
  thetaMemoryScore = 78.4,
  mobileLegibility = 'High Contrast (Optimal Mobile Visibility)',
  ffaDispersion = 72.0
}) => {
  return (
    <div>
      {/* Primary KPI: XGBoost CTR Regressor */}
      <div className="glass-card" style={{ border: '1px solid rgba(0, 255, 136, 0.3)', background: 'rgba(0, 255, 136, 0.04)' }}>
        <div className="card-title" style={{ color: 'var(--accent-green)' }}>
          <span>⚡</span> XGBoost Expected CTR Forecast
        </div>
        <div className="metric-hero-val ctr-glow">
          {predictedCtr}%
        </div>
        <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
          Expected Range: <strong>{expectedRange[0]}% – {expectedRange[1]}%</strong>
        </div>
        <div className="pill-tag pill-viral">
          {percentileTier}
        </div>
      </div>

      {/* Peer-Reviewed Cognitive & EEG Indices */}
      <div className="glass-card">
        <div className="card-title">
          <span>🧠</span> Cognitive & Neurological Indices
        </div>

        {/* Frontal Alpha Asymmetry */}
        <div style={{ marginBottom: '14px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', marginBottom: '4px' }}>
            <span style={{ color: 'var(--text-secondary)' }}>Frontal Alpha Motivation (FAA)</span>
            <strong style={{ color: faaScore >= 0 ? 'var(--accent-cyan)' : 'var(--accent-pink)' }}>
              {faaScore >= 0 ? `+${faaScore}` : faaScore} ({faaScore >= 0 ? 'Approach Pull' : 'Withdrawal'})
            </strong>
          </div>
          <div style={{ height: '6px', background: 'rgba(255,255,255,0.08)', borderRadius: '3px', overflow: 'hidden' }}>
            <div
              style={{
                width: `${Math.min(100, Math.max(0, (faaScore + 1.0) * 50))}%`,
                height: '100%',
                background: 'linear-gradient(90deg, #ff3366, #00f0ff)'
              }}
            />
          </div>
        </div>

        {/* Frontal Theta Memory Retention */}
        <div style={{ marginBottom: '14px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', marginBottom: '4px' }}>
            <span style={{ color: 'var(--text-secondary)' }}>Theta Memory Encoding (SME)</span>
            <strong style={{ color: 'var(--accent-yellow)' }}>{thetaMemoryScore}%</strong>
          </div>
          <div style={{ height: '6px', background: 'rgba(255,255,255,0.08)', borderRadius: '3px', overflow: 'hidden' }}>
            <div
              style={{
                width: `${thetaMemoryScore}%`,
                height: '100%',
                background: 'var(--accent-yellow)'
              }}
            />
          </div>
        </div>

        {/* FFA Multi-Face Attentional Dispersion */}
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', marginBottom: '4px' }}>
            <span style={{ color: 'var(--text-secondary)' }}>Fusiform Face Cannibalism (FFA)</span>
            <strong style={{ color: ffaDispersion > 60 ? 'var(--accent-pink)' : 'var(--accent-green)' }}>
              {ffaDispersion}% ({ffaDispersion > 60 ? 'High Clutter' : 'Clean Focus'})
            </strong>
          </div>
          <div style={{ height: '6px', background: 'rgba(255,255,255,0.08)', borderRadius: '3px', overflow: 'hidden' }}>
            <div
              style={{
                width: `${ffaDispersion}%`,
                height: '100%',
                background: ffaDispersion > 60 ? 'var(--accent-pink)' : 'var(--accent-green)'
              }}
            />
          </div>
        </div>
      </div>

      {/* Mobile Feeds Legibility Diagnosis */}
      <div className="glass-card">
        <div className="card-title">
          <span>📱</span> 1.5" Mobile Feed Pre-Test
        </div>
        <div style={{ fontSize: '0.85rem', color: 'var(--text-primary)', lineHeight: 1.5 }}>
          {mobileLegibility}
        </div>
      </div>
    </div>
  );
};