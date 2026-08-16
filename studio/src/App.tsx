import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { CanvasViewer } from './components/CanvasViewer';
import { ComparisonSlider } from './components/ComparisonSlider';
import { MetricsScorecard } from './components/MetricsScorecard';
import { ScanpathPlayer } from './components/ScanpathPlayer';
import './styles/main.css';

type ViewMode = 'original' | 'heatmap' | 'focus' | 'scanpath' | 'ab_comparison';
type JobPhase = 'EMPTY' | 'UPLOADING' | 'QUEUED' | 'RUNNING' | 'PARTIAL' | 'COMPLETE' | 'FAILED';

type JobState = {
  job_id: string;
  status?: string;
  stage?: number;
  progress_percent?: number;
  message?: string;
  results?: unknown;
  error?: unknown;
};

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '');
const ACCESS_TOKEN = import.meta.env.VITE_ACCESS_TOKEN || '';
const JOB_STORAGE_KEY = 'neuromarketingStudio.jobId';
const LEGACY_JOB_STORAGE_KEY = 'signalStudio.jobId';
const ACCEPTED_MEDIA = 'image/*,video/*,.pdf,.doc,.docx,.odt,.rtf,.txt,.html,.htm,.xls,.xlsx,.xlsm,.ods,.csv,.tsv,.json,.jsonl,.edf,.bdf,.fif,.set';

function mediaTypeForFile(file: File): string {
  const extension = file.name.toLowerCase().split('.').pop() || '';
  if (file.type.startsWith('image/')) return 'IMAGE';
  if (file.type.startsWith('video/')) return 'VIDEO';
  if (extension === 'pdf') return 'PDF';
  if (['doc', 'docx', 'odt', 'rtf', 'txt', 'html', 'htm'].includes(extension)) return 'DOCUMENT';
  if (['xls', 'xlsx', 'xlsm', 'ods', 'csv', 'tsv'].includes(extension)) return 'SPREADSHEET';
  if (['edf', 'bdf', 'fif', 'set', 'vhdr', 'eeg'].includes(extension)) return 'EEG';
  if (['json', 'jsonl'].includes(extension)) return 'STRUCTURED';
  return 'ASSET';
}

function parseMaybeJson(value: unknown): any {
  if (typeof value !== 'string') return value;
  try {
    return JSON.parse(value);
  } catch {
    return value;
  }
}

function normalizeEnvelope(value: unknown): any | null {
  const parsed = parseMaybeJson(value);
  if (!parsed || typeof parsed !== 'object') return null;
  const envelope = parsed.result_json ? parseMaybeJson(parsed.result_json) : parsed;
  return envelope && typeof envelope === 'object' ? envelope : null;
}

function authHeaders(): HeadersInit {
  return ACCESS_TOKEN ? { Authorization: `Bearer ${ACCESS_TOKEN}` } : {};
}

export const App = () => {
  const [viewMode, setViewMode] = useState<ViewMode>('original');
  const [heatmapOpacity, setHeatmapOpacity] = useState(0.65);
  const [currentFixationStep, setCurrentFixationStep] = useState(0);
  const [phase, setPhase] = useState<JobPhase>('EMPTY');
  const [job, setJob] = useState<JobState | null>(null);
  const [reportData, setReportData] = useState<any | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | undefined>();
  const [artifactUrls, setArtifactUrls] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const pollTimer = useRef<number | undefined>();

  const clearPolling = useCallback(() => {
    if (pollTimer.current) window.clearTimeout(pollTimer.current);
    pollTimer.current = undefined;
  }, []);

  const hydrateJob = useCallback((state: JobState) => {
    setJob(state);
    const normalized = normalizeEnvelope(state.results);
    if (normalized) setReportData(normalized);
    const normalizedStatus = (state.status || '').toUpperCase();
    if (normalizedStatus === 'COMPLETE' || normalizedStatus === 'COMPLETED') {
      setPhase('COMPLETE');
      clearPolling();
    } else if (normalizedStatus === 'FAILED') {
      setPhase('FAILED');
      clearPolling();
    } else if (normalizedStatus === 'PARTIAL') {
      setPhase('PARTIAL');
    } else if (normalizedStatus === 'RUNNING' || normalizedStatus === 'PROCESSING') {
      setPhase('RUNNING');
    } else {
      setPhase('QUEUED');
    }
  }, [clearPolling]);

  const pollJob = useCallback(async (jobId: string) => {
    if (!ACCESS_TOKEN) {
      setError('Set VITE_ACCESS_TOKEN to poll authenticated analysis jobs.');
      setPhase('FAILED');
      return;
    }
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/jobs/${encodeURIComponent(jobId)}`, { headers: authHeaders() });
      if (!response.ok) throw new Error(`Job status request failed (${response.status})`);
      const state = await response.json() as JobState;
      hydrateJob(state);
      const terminal = ['COMPLETE', 'COMPLETED', 'FAILED'].includes((state.status || '').toUpperCase());
      if (!terminal) pollTimer.current = window.setTimeout(() => void pollJob(jobId), 1800);
    } catch (pollError) {
      setError(pollError instanceof Error ? pollError.message : 'Unable to retrieve job status.');
      setPhase('FAILED');
      clearPolling();
    }
  }, [clearPolling, hydrateJob]);

  useEffect(() => {
    const savedJobId = window.localStorage.getItem(JOB_STORAGE_KEY) || window.localStorage.getItem(LEGACY_JOB_STORAGE_KEY);
    if (savedJobId && ACCESS_TOKEN) {
      setPhase('QUEUED');
      void pollJob(savedJobId);
    }
    return clearPolling;
  }, [clearPolling, pollJob]);

  useEffect(() => () => {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
  }, [previewUrl]);

  const artifactManifestKey = JSON.stringify(reportData?.artifact_file_ids || {});
  useEffect(() => {
    let cancelled = false;
    const createdUrls: string[] = [];
    const artifactIds = reportData?.artifact_file_ids || {};
    const loadArtifacts = async () => {
      if (!job?.job_id || !ACCESS_TOKEN || Object.keys(artifactIds).length === 0) {
        setArtifactUrls({});
        return;
      }
      const loaded: Record<string, string> = {};
      await Promise.all(Object.keys(artifactIds).map(async (artifactName) => {
        try {
          const response = await fetch(`${API_BASE_URL}/api/v1/jobs/${encodeURIComponent(job.job_id)}/artifacts/${encodeURIComponent(artifactName)}`, { headers: authHeaders() });
          if (!response.ok) return;
          const objectUrl = URL.createObjectURL(await response.blob());
          if (cancelled) {
            URL.revokeObjectURL(objectUrl);
          } else {
            createdUrls.push(objectUrl);
            loaded[artifactName] = objectUrl;
          }
        } catch {
          // Artifact availability is independent from numerical-result hydration.
        }
      }));
      if (!cancelled) setArtifactUrls(loaded);
    };
    void loadArtifacts();
    return () => {
      cancelled = true;
      createdUrls.forEach((objectUrl) => URL.revokeObjectURL(objectUrl));
    };
  }, [artifactManifestKey, job?.job_id]);

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file) return;
    clearPolling();
    setError(null);
    setReportData(null);
    setJob(null);
    setSelectedFile(file);
    setPreviewUrl((previous) => {
      if (previous) URL.revokeObjectURL(previous);
      return file.type.startsWith('image/') ? URL.createObjectURL(file) : undefined;
    });
    setPhase('UPLOADING');

    if (!ACCESS_TOKEN) {
      setError('Set VITE_ACCESS_TOKEN before starting an authenticated analysis.');
      setPhase('FAILED');
      return;
    }
    try {
      const bytes = new Uint8Array(await file.arrayBuffer());
      let binary = '';
      bytes.forEach((byte) => { binary += String.fromCharCode(byte); });
      const imageBase64 = btoa(binary);
      const response = await fetch(`${API_BASE_URL}/api/v1/analyze`, {
        method: 'POST',
        headers: { ...authHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ image_base64: imageBase64, filename: file.name, media_type: mediaTypeForFile(file) }),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || `Analysis request failed (${response.status})`);
      const initialState: JobState = body;
      window.localStorage.setItem(JOB_STORAGE_KEY, initialState.job_id);
      setJob(initialState);
      setPhase('QUEUED');
      void pollJob(initialState.job_id);
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : 'Unable to start analysis.');
      setPhase('FAILED');
    }
  };

  const envelope = reportData;
  const report = envelope?.report || envelope || {};
  const metrics = envelope?.neuromarketing_metrics || {};
  const visualArtifacts = report?.visual_artifacts || envelope?.canvas_overlay || {};
  const originalImage = previewUrl || artifactUrls.original_image;
  const heatmapImage = artifactUrls.thermal_heatmap;
  const focusMapImage = artifactUrls.focus_map;
  const winningVariant = artifactUrls.winning_variant;
  const scanpathData = (report?.scanpath || metrics?.scanpath || []).filter((point: any) => Number.isFinite(point?.x) && Number.isFinite(point?.y)).map((point: any, index: number) => ({
    step: Number(point.step || index + 1), x: Number(point.x), y: Number(point.y), duration_ms: Number(point.duration_ms || 0),
  }));
  const gazeVectors = (report?.biometrics?.faces || metrics?.biometrics?.faces || []).filter((face: any) => Array.isArray(face?.center_coords) && face?.gaze_vector).map((face: any) => ({
    center: [Number(face.center_coords[0]), Number(face.center_coords[1])] as [number, number], dx: Number(face.gaze_vector.dx || 0), dy: Number(face.gaze_vector.dy || 0),
  }));
  const variantLabel = report?.winning_variant || metrics?.winning_variant || 'Winning variant';
  const predictedCtr = metrics?.ctr_forecast || report?.ctr_forecast;

  const statusMessage = error || job?.message || (phase === 'EMPTY' ? 'Upload an image, video, document, PDF, spreadsheet, survey, eye-tracking export, or supported structured asset to begin a diagnostic.' : '');
  const phaseLabel = phase === 'UPLOADING' ? 'Uploading asset' : phase === 'QUEUED' ? 'Queued for analysis' : phase === 'RUNNING' ? 'Running models' : phase === 'PARTIAL' ? 'Partial results available' : phase === 'COMPLETE' ? 'Analysis complete' : phase === 'FAILED' ? 'Analysis failed' : 'Ready';

  return (
    <div className="studio-container">
      <nav className="navbar">
        <div className="brand-badge">
          <div className="brand-title">NEUROMARKETING STUDIO</div>
          <span className="version-pill">PREDICTIVE DIAGNOSTICS</span>
        </div>
        <label className="btn-action btn-primary" style={{ margin: 0, padding: '8px 16px', fontSize: '0.85rem', cursor: 'pointer' }}>
          <span>Upload asset</span>
          <input type="file" accept={ACCEPTED_MEDIA} onChange={handleFileUpload} style={{ display: 'none' }} />
        </label>
      </nav>

      <div className="studio-layout">
        <aside className="panel">
          <div className="glass-card">
            <div className="card-title"><span>Workflow</span><span className={`pill-tag ${phase === 'FAILED' ? 'pill-risk' : 'pill-viral'}`}>{phaseLabel}</span></div>
            <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>{statusMessage}</div>
            {job && <div style={{ marginTop: 12, fontSize: '0.76rem', color: 'var(--text-secondary)' }}>Job <code>{job.job_id}</code><br />Progress: {job.progress_percent ?? 0}%</div>}
            {selectedFile && <div style={{ marginTop: 12, fontSize: '0.76rem', color: 'var(--text-secondary)' }}>Asset: {selectedFile.name}</div>}
          </div>

          <div className="glass-card">
            <div className="card-title"><span>Visualization</span></div>
            <div className="toggle-group">
              {(['original', 'heatmap', 'focus', 'scanpath', 'ab_comparison'] as ViewMode[]).map((mode) => (
                <button key={mode} className={`toggle-btn ${viewMode === mode ? 'active' : ''}`} onClick={() => setViewMode(mode)} disabled={mode !== 'original' && !reportData}>
                  {mode === 'ab_comparison' ? 'A/B split' : mode}
                </button>
              ))}
            </div>
            {viewMode === 'heatmap' && <div className="slider-container"><div className="slider-label"><span>Overlay opacity</span><strong>{Math.round(heatmapOpacity * 100)}%</strong></div><input type="range" min={0.1} max={1} step={0.05} value={heatmapOpacity} onChange={(e) => setHeatmapOpacity(Number(e.target.value))} /></div>}
          </div>

          {scanpathData.length > 0 && <ScanpathPlayer totalSteps={scanpathData.length} currentStep={Math.min(currentFixationStep, scanpathData.length)} onStepChange={setCurrentFixationStep} />}

          <div className="glass-card">
            <div className="card-title"><span>Evidence policy</span></div>
            <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
              Model-predicted attention is shown separately from measured participant outcomes. A score is not a diagnosis, causal effect, or guaranteed conversion result.
            </div>
          </div>
        </aside>

        <main className="canvas-workspace">
          {!originalImage ? (
            <div style={{ textAlign: 'center', maxWidth: 420 }}><div className="metric-hero-val" style={{ fontSize: '1.4rem', marginBottom: 12 }}>Start with an asset</div><div style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', lineHeight: 1.5 }}>Upload a raster creative. The client will retain a local preview while the authenticated worker produces model outputs.</div></div>
          ) : viewMode === 'ab_comparison' && winningVariant ? (
            <ComparisonSlider originalImage={originalImage} variantImage={winningVariant} variantLabel={variantLabel} liftPct={Number(metrics?.variant_lift_pct || 0)} />
          ) : (
            <CanvasViewer imageSrc={originalImage} heatmapSrc={heatmapImage} focusMapSrc={focusMapImage} viewMode={viewMode === 'ab_comparison' ? 'original' : viewMode} heatmapOpacity={heatmapOpacity} scanpath={scanpathData} gazeVectors={gazeVectors} currentStep={currentFixationStep} />
          )}
        </main>

        <aside className="panel panel-right">
          <MetricsScorecard report={report} metrics={metrics} />
        </aside>
      </div>
    </div>
  );
};

export default App;
