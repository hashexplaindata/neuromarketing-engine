"""Canonical contracts shared by the API, workers, providers, experiments, and reports.

The contract deliberately separates measured observations, model predictions, and
heuristic proxies. It is the system-of-record shape for Phase 1; providers may
return richer raw payloads, but public result objects must validate against these
models before being persisted or rendered.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class JobStatus(str, Enum):
    CREATED = "CREATED"
    UPLOADING = "UPLOADING"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    PARTIAL = "PARTIAL"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class ExperimentMode(str, Enum):
    PREDICTIVE = "PREDICTIVE"
    EMPIRICAL = "EMPIRICAL"


class ProviderStatus(str, Enum):
    NOT_CONFIGURED = "NOT_CONFIGURED"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class EvidenceClass(str, Enum):
    MEASURED = "MEASURED"
    MODEL_PREDICTED = "MODEL_PREDICTED"
    DERIVED_PROXY = "DERIVED_PROXY"
    HEURISTIC = "HEURISTIC"


class ArtifactKind(str, Enum):
    ORIGINAL = "ORIGINAL"
    PREVIEW = "PREVIEW"
    HEATMAP = "HEATMAP"
    OVERLAY = "OVERLAY"
    SCANPATH = "SCANPATH"
    REPORT_HTML = "REPORT_HTML"
    REPORT_PDF = "REPORT_PDF"
    REPORT_JSON = "REPORT_JSON"
    REPORT_CSV = "REPORT_CSV"
    REPORT_XLSX = "REPORT_XLSX"
    DEBUG = "DEBUG"


class MetricValue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str = Field(min_length=1, max_length=120)
    label: str = Field(min_length=1, max_length=240)
    value: Optional[float | int | str | bool] = None
    unit: Optional[str] = Field(default=None, max_length=80)
    evidence_class: EvidenceClass
    provider_id: str = Field(min_length=1, max_length=160)
    provider_version: Optional[str] = Field(default=None, max_length=160)
    formula: Optional[str] = None
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    validation_status: Literal["VALIDATED", "UNVALIDATED", "NOT_APPLICABLE", "UNAVAILABLE"]
    interpretation: Optional[str] = None
    limitations: List[str] = Field(default_factory=list)
    source_result_ids: List[str] = Field(default_factory=list)


class ProviderResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider_id: str = Field(min_length=1, max_length=160)
    provider_name: str = Field(min_length=1, max_length=240)
    provider_version: Optional[str] = Field(default=None, max_length=160)
    input_kinds: List[str] = Field(default_factory=list)
    status: ProviderStatus
    evidence_class: EvidenceClass
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metrics: List[MetricValue] = Field(default_factory=list)
    artifact_ids: List[str] = Field(default_factory=list)
    raw_output_ref: Optional[str] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)


class ArtifactRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    artifact_id: str = Field(min_length=1, max_length=160)
    kind: ArtifactKind
    media_type: str = Field(min_length=1, max_length=160)
    storage_key: str = Field(min_length=1, max_length=500)
    sha256: Optional[str] = Field(default=None, min_length=64, max_length=64)
    byte_size: Optional[int] = Field(default=None, ge=0)
    width: Optional[int] = Field(default=None, ge=1)
    height: Optional[int] = Field(default=None, ge=1)
    duration_ms: Optional[int] = Field(default=None, ge=0)
    signed_url: Optional[str] = None
    expires_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class JobError(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1, max_length=120)
    message: str = Field(min_length=1, max_length=1000)
    retryable: bool = False
    provider_id: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)


class JobRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_id: str = Field(min_length=1, max_length=160)
    tenant_id: str = Field(min_length=1, max_length=160)
    project_id: str = Field(min_length=1, max_length=160)
    user_id: str = Field(min_length=1, max_length=160)
    experiment_id: Optional[str] = None
    asset_id: str = Field(min_length=1, max_length=160)
    status: JobStatus = JobStatus.CREATED
    progress_percent: int = Field(default=0, ge=0, le=100)
    current_stage: Optional[str] = None
    idempotency_key: Optional[str] = None
    attempt: int = Field(default=0, ge=0)
    max_attempts: int = Field(default=3, ge=1, le=10)
    provider_ids: List[str] = Field(default_factory=list)
    provider_results: List[ProviderResult] = Field(default_factory=list)
    artifact_ids: List[str] = Field(default_factory=list)
    error: Optional[JobError] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class ExperimentFactor(BaseModel):
    model_config = ConfigDict(extra="forbid")

    factor_id: str = Field(min_length=1, max_length=120)
    label: str = Field(min_length=1, max_length=240)
    levels: List[str] = Field(min_length=2)


class ExperimentSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    experiment_id: str = Field(min_length=1, max_length=160)
    tenant_id: str = Field(min_length=1, max_length=160)
    project_id: str = Field(min_length=1, max_length=160)
    mode: ExperimentMode
    factors: List[ExperimentFactor] = Field(default_factory=list)
    condition_ids: List[str] = Field(default_factory=list)
    unit_of_analysis: str = Field(min_length=1, max_length=120)
    primary_outcome: str = Field(min_length=1, max_length=160)
    secondary_outcomes: List[str] = Field(default_factory=list)
    analysis_method: Optional[str] = None
    correction_method: Optional[str] = None
    preregistered: bool = False
    randomisation_seed: Optional[int] = None


class AnalysisResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "1.0.0"
    analysis_id: str = Field(min_length=1, max_length=160)
    tenant_id: str = Field(min_length=1, max_length=160)
    project_id: str = Field(min_length=1, max_length=160)
    asset_id: str = Field(min_length=1, max_length=160)
    job_id: str = Field(min_length=1, max_length=160)
    mode: ExperimentMode = ExperimentMode.PREDICTIVE
    status: JobStatus
    providers: List[ProviderResult] = Field(default_factory=list)
    metrics: List[MetricValue] = Field(default_factory=list)
    artifacts: List[ArtifactRef] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    errors: List[JobError] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None


class ProgressEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_id: str
    status: JobStatus
    stage: str
    progress_percent: int = Field(ge=0, le=100)
    message: str
    provider_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ReportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    analysis_id: str
    audience: Literal["EXECUTIVE", "MARKETER", "DESIGNER", "SCIENTIST", "BEHAVIOURAL_SCIENTIST", "GENERAL"] = "MARKETER"
    formats: List[ArtifactKind] = Field(default_factory=lambda: [ArtifactKind.REPORT_HTML, ArtifactKind.REPORT_PDF, ArtifactKind.REPORT_JSON])
    include_raw_outputs: bool = False
    include_technical_appendix: bool = True
    gemini_narrative: bool = True
