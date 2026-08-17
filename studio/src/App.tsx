import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { CanvasViewer } from './components/CanvasViewer';
import './styles/main.css';

type ViewMode = 'original' | 'heatmap' | 'focus';
type Phase = 'READY' | 'DRAFT' | 'UPLOADING' | 'QUEUED' | 'RUNNING' | 'COMPLETE' | 'FAILED';
type Objective = 'OVERALL_HIERARCHY' | 'BRAND_VISIBILITY' | 'CTA_VISIBILITY' | 'HEADLINE_CLARITY';

type JobState = {
  job_id: string;
  status?: string;
  progress_percent?: number;
  message?: string;
  results?: unknown;
  error?: unknown;
};

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '');
const ACCESS_TOKEN = import.meta.env.VITE_ACCESS_TOKEN || '';
const JOB_STORAGE_KEY = 'neuromarketingStudio.mvp.jobId';
const MAX_IMAGE_BYTES = 8 * 1024 * 1024;
const ACCEPTED_MEDIA = 'image/jpeg,image/png,image/webp';

const OBJECTIVES: Array<{ value: Objective; label: string; description: string }> = [
  { value: 'OVERALL_HIERARCHY', label: 'Overall visual hierarchy', description: 'Is the creative’s main message likely to stand out clearly?' },
  { value: 'BRAND_VISIBILITY', label: 'Brand visibility', description: 'Is the brand or logo likely to receive enough visual priority?' },
  { value: 'CTA_VISIBILITY', label: 'CTA visibility', description: 'Is the action or offer visually easy to find?' },
  { value: 'HEADLINE_CLARITY', label: 'Headline clarity', description: 'Does the headline compete effectively with other elements?' },
];

const artifactLabels: Record<string, string> = {
  report_html: 'Open HTML report',
  report_pdf: 'Download PDF report',
  report_json: 'Download JSON evidence',
  report_csv: 'Download CSV metrics',
  report_xlsx: 'Download Excel workbook',
};

function parseMaybeJson(value: unknown): any {
  if (typeof value !== 'string') return value;
  try { return JSON.parse(value); } catch { return value; }
}

function normalizeEnvelope(value: unknown): any | null {
  const parsed = parseMaybeJson(value);
  if (!parsed || typeof parsed !== 'object') return null;
  const envelope = parsed.result_json ? parseMaybeJson(parsed.result_json) : parsed;
  return envelope && typeof envelope === 'object' ? envelope : null;
}

function mediaTypeForFile(file: File): string {
  return file.type.startsWith('image/') ? 'IMAGE' : 'ASSET';
}

function authHeaders(): HeadersInit {
  return ACCESS_TOKEN ? { Authorization: `Bearer ${ACCESS_TOKEN}` } : {};
}

function numberOrNull(value: unknown): number | null {
  const parsed = typeof value === 'number' ? value : Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function formatNumber(value: unknown, digits = 1): string {
  const parsed = numberOrNull(value);
  return parsed === null ? '—' : parsed.toFixed(digits);
}

function reportFrom(job: JobState | null): any {
  const envelope = normalizeEnvelope(job?.results);
  return envelope?.report || envelope || {};
}

function objectiveText(objective: Objective): string {
  return OBJECTIVES.find((item) => item.value === objective)?.description || '';
}

function createFindings(report: any, objective: Objective): string[] {
  const metrics = report?.metrics || {};
  const complexity = numberOrNull(metrics?.cognitive_load?.cognitive_load_index);
  const legibility = numberOrNull(report?.linguistics?.mobile_legibility_score);
  const textCount = numberOrNull(report?.linguistics?.detected_text_count) || 0;
  const detections = Array.isArray(report?.detections) ? report.detections : [];
  const strongest = [...detections]
    .filter((item) => numberOrNull(item?.fixation_share_pct) !== null)
    .sort((a, b) => Number(b.fixation_share_pct) - Number(a.fixation_share_pct))[0];
  const findings: string[] = [];

  if (strongest) findings.push(`${strongest.label || 'The strongest detected region'} receives the largest predicted saliency share among detected regions (${formatNumber(strongest.fixation_share_pct)}%).`);
  else findings.push('No reliable candidate region was detected, so the attention map should be interpreted at the whole-image level.');
  if (objective === 'CTA_VISIBILITY') findings.push('Review whether the CTA is one of the highest-priority regions; the current model output does not prove that viewers will click it.');
  else if (objective === 'BRAND_VISIBILITY') findings.push('Review the brand/logo candidate against the strongest predicted region before deciding whether its visual priority is sufficient.');
  else if (objective === 'HEADLINE_CLARITY') findings.push('Compare the headline candidate with nearby text and image regions to check whether the intended reading order is visually supported.');
  else findings.push('Use the predicted map to check whether the intended message competes with secondary elements before producing another version.');
  if (complexity !== null && complexity >= 60) findings.push(`The visual-complexity proxy is ${formatNumber(complexity)}/100, suggesting that simplification may be worth testing.`);
  else if (legibility !== null && legibility < 55) findings.push(`The detected text has a lower mobile-legibility proxy (${formatNumber(legibility)}/100); test stronger local contrast or fewer competing text blocks.`);
  else if (textCount === 0) findings.push('No text regions were detected. Confirm that important copy is visible and legible in the uploaded asset.');
  else findings.push('The detected text and layout should be reviewed against the intended message hierarchy before launch.');
  return findings.slice(0, 3);
}

function createRecommendations(report: any, objective: Objective): string[] {
  const metrics = report?.metrics || {};
  const complexity = numberOrNull(metrics?.cognitive_load?.cognitive_load_index);
  const legibility = numberOrNull(report?.linguistics?.mobile_legibility_score);
  const lead = objective === 'CTA_VISIBILITY' ? 'Increase CTA contrast or separation' : objective === 'BRAND_VISIBILITY' ? 'Increase brand/logo prominence' : objective === 'HEADLINE_CLARITY' ? 'Strengthen headline hierarchy' : 'Create a simpler hierarchy between the main message and secondary elements';
  const recommendations = [
    `${lead}, then rerun the same diagnostic on a controlled revision.`,
    'Confirm the candidate regions manually before making a final creative decision.',
  ];
  if (complexity !== null && complexity >= 60) recommendations.push('Remove or reduce one competing visual element and compare the revised version.');
  else if (legibility !== null && legibility < 55) recommendations.push('Test a higher-contrast text treatment at the intended mobile display size.');
  else recommendations.push('Test one change at a time so the visual difference can be attributed to a specific design decision.');
  return recommendations;
}

export default function App() {
  const [objective, setObjective] = useState<Objective>('OVERALL_HIERARCHY');
  const [phase, setPhase] = useState<Phase>('READY');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string>();
  const [job, setJob] = useState<JobState | null>(null);
  const [artifactUrls, setArtifactUrls] = useState<Record<string, string>>({});
  const [viewMode, setViewMode] = useState<ViewMode>('original');
  const [heatmapOpacity, setHeatmapOpacity] = useState(0.7);
  const [error, setError] = useState<string | null>(null);
  const pollTimer = useRef<number>();
  const activeJobId = useRef<string | null>(null);

  const report = reportFrom(job);
  const metrics = report?.metrics || {};
  const detections = Array.isArray(report?.detections) ? report.detections : [];
  const candidateRegions = detections
    .filter((item: any) => Array.isArray(item?.bbox) && numberOrNull(item?.fixation_share_pct) !== null)
    .sort((a: any, b: any) => Number(b.fixation_share_pct) - Number(a.fixation_share_pct))
    .slice(0, 6);
  const findings = useMemo(() => createFindings(report, objective), [report, objective]);
  const recommendations = useMemo(() => createRecommendations(report, objective), [report, objective]);
  const isBusy = phase === 'UPLOADING' || phase === 'QUEUED' || phase === 'RUNNING';
  const objectiveLabel = OBJECTIVES.find((item) => item.value === objective)?.label || 'Creative diagnostic';

  const clearPolling = useCallback(() => {
    if (pollTimer.current) window.clearTimeout(pollTimer.current);
    pollTimer.current = undefined;
  }, []);

  const hydrate = useCallback((state: JobState) => {
    setJob(state);
    const status = (state.status || '').toUpperCase();
    if (status === 'COMPLETE' || status === 'COMPLETED') { setPhase('COMPLETE'); clearPolling(); }
    else if (status === 'FAILED') { setPhase('FAILED'); clearPolling(); }
    else if (status === 'RUNNING' || status === 'PROCESSING') setPhase('RUNNING');
    else setPhase('QUEUED');
  }, [clearPolling]);

  const pollJob = useCallback(async (jobId: string) => {
    if (activeJobId.current !== jobId || !ACCESS_TOKEN) return;
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/jobs/${encodeURIComponent(jobId)}`, { headers: authHeaders() });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || `Analysis status failed (${response.status})`);
      hydrate(body as JobState);
      if (!['COMPLETE', 'COMPLETED', 'FAILED'].includes(String(body.status || '').toUpperCase())) {
        pollTimer.current = window.setTimeout(() => void pollJob(jobId), 1200);
      }
    } catch (pollError) {
      setError(pollError instanceof Error ? pollError.message : 'Unable to retrieve analysis status.');
      setPhase('FAILED');
      clearPolling();
    }
  }, [clearPolling, hydrate]);

  useEffect(() => {
    const saved = window.localStorage.getItem(JOB_STORAGE_KEY);
    if (saved && ACCESS_TOKEN) { activeJobId.current = saved; setPhase('QUEUED'); void pollJob(saved); }
    return clearPolling;
  }, [clearPolling, pollJob]);

  useEffect(() => () => { if (previewUrl) URL.revokeObjectURL(previewUrl); }, [previewUrl]);

  useEffect(() => {
    let cancelled = false;
    const loadArtifacts = async () => {
      const ids = normalizeEnvelope(job?.results)?.artifact_file_ids || {};
      if (!job?.job_id || !ACCESS_TOKEN || Object.keys(ids).length === 0) { setArtifactUrls({}); return; }
      const loaded: Record<string, string> = {};
      await Promise.all(Object.keys(ids).map(async (name) => {
        try {
          const response = await fetch(`${API_BASE_URL}/api/v1/jobs/${encodeURIComponent(job.job_id)}/artifacts/${encodeURIComponent(name)}`, { headers: authHeaders() });
          if (response.ok) loaded[name] = URL.createObjectURL(await response.blob());
        } catch { /* Individual artifacts may arrive after the numeric result. */ }
      }));
      if (!cancelled) setArtifactUrls(loaded); else Object.values(loaded).forEach(URL.revokeObjectURL);
    };
    void loadArtifacts();
    return () => { cancelled = true; };
  }, [job?.job_id, job?.results]);

  const reset = () => {
    clearPolling();
    activeJobId.current = null;
    window.localStorage.removeItem(JOB_STORAGE_KEY);
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    Object.values(artifactUrls).forEach(URL.revokeObjectURL);
    setSelectedFile(null); setPreviewUrl(undefined); setJob(null); setArtifactUrls({}); setError(null); setPhase('READY'); setViewMode('original');
  };

  const handleFileSelected = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file) return;
    reset();
    setSelectedFile(file);
    setPreviewUrl(URL.createObjectURL(file));
    if (!ACCESS_TOKEN) { setError('This preview has no authenticated API session. Configure VITE_ACCESS_TOKEN locally before running a client analysis.'); setPhase('FAILED'); return; }
    if (file.size > MAX_IMAGE_BYTES) { setError('For this MVP, choose an image smaller than 8 MB.'); setPhase('FAILED'); return; }
    setError(null); setPhase('DRAFT');
  };

  const runAnalysis = async () => {
    if (!selectedFile || isBusy) return;
    if (!ACCESS_TOKEN) { setError('This preview has no authenticated API session. Configure VITE_ACCESS_TOKEN locally before running a client analysis.'); setPhase('FAILED'); return; }
    setError(null); setPhase('UPLOADING');
    try {
      const formData = new FormData();
      formData.append('file', selectedFile, selectedFile.name);
      const uploadResponse = await fetch(`${API_BASE_URL}/api/v1/assets/upload`, {
        method: 'POST',
        headers: authHeaders(),
        body: formData,
      });
      const uploadBody = await uploadResponse.json().catch(() => ({}));
      if (!uploadResponse.ok || !uploadBody.file_id) throw new Error(uploadBody.detail || `Could not upload creative (${uploadResponse.status})`);

      const response = await fetch(`${API_BASE_URL}/api/v1/analyze`, {
        method: 'POST',
        headers: { ...authHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ file_id: uploadBody.file_id, filename: selectedFile.name, media_type: mediaTypeForFile(selectedFile), domain_module: 'UI_UX_AND_DIGITAL_ADS', project_id: objective, objective }),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || `Could not start analysis (${response.status})`);
      activeJobId.current = body.job_id;
      window.localStorage.setItem(JOB_STORAGE_KEY, body.job_id);
      setJob(body as JobState); setPhase('QUEUED'); void pollJob(body.job_id);
    } catch (analysisError) {
      setError(analysisError instanceof Error ? analysisError.message : 'Could not start analysis.');
      setPhase('FAILED');
    }
  };

  const originalImage = previewUrl || artifactUrls.original_image;
  const viewImage = viewMode === 'heatmap' ? artifactUrls.thermal_heatmap : viewMode === 'focus' ? artifactUrls.focus_map : undefined;
  const scanpath = (report?.scanpath || []).filter((point: any) => Number.isFinite(point?.x) && Number.isFinite(point?.y)).map((point: any, index: number) => ({ step: Number(point.step || index + 1), x: Number(point.x), y: Number(point.y), duration_ms: Number(point.duration_ms || 0) }));
  const statusLabel = phase === 'READY' ? 'Ready' : phase === 'DRAFT' ? 'Ready to run' : phase === 'UPLOADING' ? 'Uploading' : phase === 'QUEUED' ? 'Queued' : phase === 'RUNNING' ? 'Analysing' : phase === 'COMPLETE' ? 'Complete' : 'Needs attention';
  const evidenceStatus = report?.evidence_status || 'MODEL_PREDICTED';
  const complexity = metrics?.cognitive_load?.cognitive_load_index;
  const legibility = report?.linguistics?.mobile_legibility_score;

  return (
    <div className="mvp-shell">
      <header className="mvp-header">
        <div>
          <div className="mvp-brand">NEUROMARKETING STUDIO</div>
          <div className="mvp-tagline">Static creative pre-flight diagnostics</div>
        </div>
        <div className="mvp-header-actions">
          <span className={`connection-pill ${ACCESS_TOKEN ? 'connected' : 'warning'}`}>{ACCESS_TOKEN ? 'Session ready' : 'Session required'}</span>
          <label className="primary-button"><span>{isBusy ? 'Analysing…' : 'Choose creative'}</span><input type="file" accept={ACCEPTED_MEDIA} onChange={handleFileSelected} disabled={isBusy} /></label>
          {(selectedFile || job) && <button className="quiet-button" onClick={reset}>Start over</button>}
        </div>
      </header>

      <main className="mvp-grid">
        <aside className="setup-column">
          <section className="mvp-card setup-card">
            <div className="section-kicker">01 / SET THE QUESTION</div>
            <h1>Test a creative</h1>
            <p className="muted">Choose the decision you need to make. The analysis stays focused on that question.</p>
            <label className="field-label" htmlFor="objective">Diagnostic objective</label>
            <select id="objective" className="mvp-select" value={objective} onChange={(event) => setObjective(event.target.value as Objective)} disabled={isBusy}>
              {OBJECTIVES.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
            </select>
            <p className="field-help">{objectiveText(objective)}</p>
          </section>

          <section className="mvp-card upload-card">
            <div className="section-kicker">02 / ADD THE ASSET</div>
            <label className="dropzone">
              <span className="upload-symbol">＋</span>
              <strong>{selectedFile ? selectedFile.name : 'Upload a JPG, PNG, or WebP'}</strong>
              <span>{selectedFile ? `${(selectedFile.size / 1024 / 1024).toFixed(2)} MB · ready for review` : 'Maximum 8 MB for this MVP'}</span>
              <input type="file" accept={ACCEPTED_MEDIA} onChange={handleFileSelected} disabled={isBusy} />
            </label>
            {selectedFile && <button type="button" className="primary-button run-button" onClick={() => void runAnalysis()} disabled={phase !== 'DRAFT'}>Run Analysis</button>}
          </section>

          <section className={`mvp-card status-card ${phase === 'FAILED' ? 'error-card' : ''}`}>
            <div className="status-line"><span className={`status-dot ${phase.toLowerCase()}`} /><strong>{statusLabel}</strong>{job?.progress_percent !== undefined && <span>{job.progress_percent}%</span>}</div>
            <p className="muted">{error || (phase === 'READY' ? 'Choose a creative to prepare a diagnostic.' : phase === 'DRAFT' ? 'Review the creative and objective, then run the diagnostic when ready.' : job?.message || 'Working through the selected creative.')}</p>
            {phase === 'FAILED' && <button className="secondary-button" onClick={() => { setError(null); setPhase(selectedFile ? 'DRAFT' : 'READY'); }}>Try again</button>}
          </section>

          <section className="mvp-card boundary-card">
            <div className="section-kicker">EVIDENCE BOUNDARY</div>
            <p>These are model-predicted visual-attention and image-structure diagnostics. They are not measured participant gaze, emotion, neural activity, clicks, conversion, or causal lift.</p>
          </section>
        </aside>

        <section className="results-column">
          {!originalImage ? (
            <div className="welcome-panel">
              <div className="welcome-mark">◎</div>
              <div className="section-kicker">A SIMPLE START</div>
              <h2>Find the visual decision hiding inside your creative.</h2>
              <p>Upload one ad, review the predicted visual hierarchy, and leave with a clear next test. No technical configuration is required.</p>
              <label className="primary-button large-button">Choose a creative<input type="file" accept={ACCEPTED_MEDIA} onChange={handleFileSelected} /></label>
              <div className="three-step"><span><b>1</b> Question</span><span><b>2</b> Creative</span><span><b>3</b> Decision</span></div>
            </div>
          ) : (
            <>
              <div className="result-heading"><div><div className="section-kicker">03 / REVIEW THE EVIDENCE</div><h2>{objectiveLabel}</h2><p className="muted">{selectedFile?.name}</p></div><span className={`result-pill ${phase.toLowerCase()}`}>{statusLabel}</span></div>
              <div className="canvas-card">
                <div className="canvas-tabs">{(['original', 'heatmap', 'focus'] as ViewMode[]).map((mode) => <button key={mode} className={viewMode === mode ? 'active' : ''} onClick={() => setViewMode(mode)} disabled={mode !== 'original' && !report}>{mode === 'original' ? 'Original' : mode === 'heatmap' ? 'Attention map' : 'Focus map'}</button>)}</div>
                <CanvasViewer imageSrc={originalImage} heatmapSrc={artifactUrls.thermal_heatmap} focusMapSrc={artifactUrls.focus_map} viewMode={viewMode} heatmapOpacity={heatmapOpacity} scanpath={scanpath} gazeVectors={[]} currentStep={0} />
                {viewMode === 'heatmap' && <div className="opacity-control"><span>Map opacity</span><input type="range" min="0.2" max="1" step="0.05" value={heatmapOpacity} onChange={(event) => setHeatmapOpacity(Number(event.target.value))} /></div>}
              </div>
              {report && phase === 'COMPLETE' && <div className="decision-banner"><div><div className="section-kicker">DECISION SUMMARY</div><strong>{findings[0] || 'Review the evidence before deciding what to test next.'}</strong></div><span className="evidence-badge">{evidenceStatus}</span></div>}
            </>
          )}
        </section>

        <aside className="insight-column">
          <section className="mvp-card insight-card">
            <div className="section-kicker">QUICK READ</div>
            <h3>What the model sees</h3>
            <div className="metric-list">
              <div><span>Predicted concentration</span><strong>{formatNumber(metrics?.nss, 2)}</strong><small>model output · not accuracy</small></div>
              <div><span>Visual complexity proxy</span><strong>{complexity === undefined ? '—' : `${formatNumber(complexity)}/100`}</strong><small>derived from image structure</small></div>
              <div><span>Text legibility proxy</span><strong>{legibility === undefined ? '—' : `${formatNumber(legibility)}/100`}</strong><small>detected text only</small></div>
            </div>
          </section>

          {phase === 'COMPLETE' && <>
            <section className="mvp-card">
              <div className="section-kicker">FINDINGS</div>
              <h3>What to notice</h3>
              <ol className="finding-list">{findings.map((finding, index) => <li key={`${index}-${finding}`}>{finding}</li>)}</ol>
            </section>
            <section className="mvp-card">
              <div className="section-kicker">NEXT TEST</div>
              <h3>What to try next</h3>
              <ol className="finding-list recommendation-list">{recommendations.map((item, index) => <li key={`${index}-${item}`}>{item}</li>)}</ol>
            </section>
          </>}

          {candidateRegions.length > 0 && <section className="mvp-card">
            <div className="section-kicker">CANDIDATE REGIONS</div>
            <h3>Predicted visual priority</h3>
            <p className="field-help">These regions are automatically detected and should be reviewed before being treated as formal AOIs.</p>
            <div className="region-list">{candidateRegions.map((item: any, index: number) => <div className="region-row" key={`${item.label}-${index}`}><span>{item.label || 'Detected region'}</span><strong>{formatNumber(item.fixation_share_pct)}%</strong></div>)}</div>
          </section>}

          <section className="mvp-card report-card">
            <div className="section-kicker">REPORT</div>
            <h3>{phase === 'COMPLETE' ? 'Ready to share' : 'Report after analysis'}</h3>
            {phase === 'COMPLETE' && Object.keys(artifactUrls).filter((name) => name.startsWith('report_')).length > 0 ? <div className="report-links">{Object.entries(artifactUrls).filter(([name]) => name.startsWith('report_')).map(([name, url]) => <a href={url} download key={name}>{artifactLabels[name] || name}<span>↗</span></a>)}</div> : <p className="muted">The report will include the evidence status, visual diagnostics, limitations, and next-test recommendations.</p>}
          </section>
        </aside>
      </main>
    </div>
  );
}
