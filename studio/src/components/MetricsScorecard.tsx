type MetricsScorecardProps = {
  report?: any;
  metrics?: any;
};

const numberOrNull = (value: unknown): number | null => {
  const parsed = typeof value === 'number' ? value : Number(value);
  return Number.isFinite(parsed) ? parsed : null;
};

const displayNumber = (value: unknown, digits = 2): string => {
  const parsed = numberOrNull(value);
  return parsed === null ? '—' : parsed.toFixed(digits);
};

export const MetricsScorecard = ({ report = {}, metrics = {} }: MetricsScorecardProps) => {
  const domainKpis = metrics.domain_kpis || {};
  const forecast = metrics.ctr_forecast || report.ctr_forecast || {};
  const sAuc = metrics.s_auc ?? domainKpis.s_auc ?? report.metrics?.s_auc;
  const nss = metrics.nss_score ?? domainKpis.nss ?? domainKpis.nss_score ?? report.metrics?.nss;
  const cognitiveLoad = metrics.cognitive_load_score ?? domainKpis.cognitive_load?.cognitive_load_index ?? report.metrics?.cognitive_load?.cognitive_load_index;
  const evidenceStatus = report.evidence_status || 'MODEL_PREDICTED';
  const limitations = Array.isArray(report.limitations) ? report.limitations : [];
  const expectedRange = Array.isArray(forecast.expected_range_pct) ? forecast.expected_range_pct : null;

  return (
    <div>
      <div className="glass-card" style={{ border: '1px solid rgba(0, 255, 136, 0.3)', background: 'rgba(0, 255, 136, 0.04)' }}>
        <div className="card-title" style={{ color: 'var(--accent-green)' }}><span>CTR forecast</span><span className="pill-tag pill-viral">{evidenceStatus}</span></div>
        <div className="metric-hero-val ctr-glow">{displayNumber(forecast.predicted_ctr_pct)}{numberOrNull(forecast.predicted_ctr_pct) === null ? '' : '%'}</div>
        <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: 4 }}>
          Expected range: <strong>{expectedRange ? `${displayNumber(expectedRange[0])}% – ${displayNumber(expectedRange[1])}%` : 'Not available'}</strong>
        </div>
        {forecast.industry_percentile && <div className="pill-tag pill-viral">{forecast.industry_percentile}</div>}
      </div>

      <div className="glass-card">
        <div className="card-title"><span>Visual-attention metrics</span></div>
        <MetricRow label="s-AUC" value={displayNumber(sAuc, 3)} note="Model discriminability" />
        <MetricRow label="NSS" value={displayNumber(nss, 3)} note="Saliency concentration" />
        <MetricRow label="Visual complexity proxy" value={cognitiveLoad === null ? '—' : `${displayNumber(cognitiveLoad, 1)}/100`} note="Derived from image features" />
      </div>

      <div className="glass-card">
        <div className="card-title"><span>Interpretation boundary</span></div>
        <div style={{ fontSize: '0.82rem', color: 'var(--text-primary)', lineHeight: 1.5 }}>
          These outputs are computational predictions from pretrained models. They do not establish participant attention, memory, emotion, EEG, causal lift, or guaranteed conversion.
        </div>
        {limitations.length > 0 && <ul style={{ margin: '12px 0 0 18px', padding: 0, color: 'var(--text-secondary)', fontSize: '0.76rem', lineHeight: 1.5 }}>{limitations.slice(0, 3).map((limitation: string, index: number) => <li key={`${index}-${limitation}`}>{limitation}</li>)}</ul>}
      </div>
    </div>
  );
};

const MetricRow = ({ label, value, note }: { label: string; value: string; note: string }) => (
  <div style={{ marginBottom: 14 }}>
    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.86rem', marginBottom: 4 }}><span style={{ color: 'var(--text-secondary)' }}>{label}</span><strong style={{ color: 'var(--accent-cyan)' }}>{value}</strong></div>
    <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>{note}</div>
  </div>
);
