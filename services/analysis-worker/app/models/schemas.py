from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum


class SemanticRole(str, Enum):
    record_id = "record_id"
    case_id = "case_id"
    activity_name = "activity_name"
    state = "state"
    status = "status"
    created_at = "created_at"
    updated_at = "updated_at"
    resolved_at = "resolved_at"
    closed_at = "closed_at"
    assignee = "assignee"
    assignment_group = "assignment_group"
    customer = "customer"
    category = "category"
    subcategory = "subcategory"
    priority = "priority"
    sla_breach_flag = "sla_breach_flag"
    satisfaction_score = "satisfaction_score"
    comment_text = "comment_text"
    description = "description"
    duration = "duration"
    channel = "channel"
    source_system = "source_system"
    region = "region"
    queue = "queue"
    unknown = "unknown"


class ColumnProfile(BaseModel):
    column_name: str
    inferred_type: str
    null_count: int
    null_ratio: float
    distinct_count: int
    distinct_ratio: float
    is_enum_like: bool
    is_free_text: bool
    sample_values: List[str]
    min_value: Optional[str] = None
    max_value: Optional[str] = None
    mean_value: Optional[float] = None
    median_value: Optional[float] = None
    std_dev: Optional[float] = None
    p25: Optional[float] = None
    p75: Optional[float] = None
    p95: Optional[float] = None
    timestamp_parse_success_ratio: Optional[float] = None
    top_values: Optional[List[Dict[str, Any]]] = None


class SemanticInference(BaseModel):
    column_name: str
    inferred_role: SemanticRole
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str
    sample_justification: str
    alternative_roles: List[Dict[str, Any]] = []


class ProcessReadinessScore(BaseModel):
    overall: float
    timeline_quality: float
    case_traceability: float
    activity_clarity: float
    actor_clarity: float
    customer_segmentation: float
    recommendation_confidence: float
    warnings: List[str]


class ProfilingRequest(BaseModel):
    dataset_id: str
    file_path: str
    parquet_output_path: str
    job_id: str


class ProfilingResult(BaseModel):
    dataset_id: str
    profiling_run_id: str
    row_count: int
    column_count: int
    file_size_bytes: int
    delimiter: str
    encoding: str
    has_header: bool
    columns: List[ColumnProfile]
    semantic_inferences: List[SemanticInference]
    process_readiness: ProcessReadinessScore
    completed_at: str


class MappingDecision(BaseModel):
    dataset_id: str
    case_id_column: Optional[str] = None
    activity_column: Optional[str] = None
    created_at_column: Optional[str] = None
    updated_at_column: Optional[str] = None
    resolved_at_column: Optional[str] = None
    closed_at_column: Optional[str] = None
    assignee_column: Optional[str] = None
    assignment_group_column: Optional[str] = None
    customer_column: Optional[str] = None
    satisfaction_column: Optional[str] = None
    priority_column: Optional[str] = None
    category_column: Optional[str] = None
    subcategory_column: Optional[str] = None
    status_column: Optional[str] = None
    additional_dimensions: Optional[Dict[str, str]] = None


class AnalysisRequest(BaseModel):
    dataset_id: str
    analysis_run_id: str
    parquet_path: str
    mapping: MappingDecision
    job_id: str


class InsightCandidate(BaseModel):
    insight_id: str
    insight_type: str
    title: str
    description_seed: str
    support_count: int
    impacted_population_pct: float
    comparison_baseline: Optional[str] = None
    effect_size: float
    confidence: float
    evidence_refs: Dict[str, Any]
    recommended_action_seed: str
    rank_score: float


class AnalysisResult(BaseModel):
    dataset_id: str
    analysis_run_id: str
    metrics: Dict[str, Any]
    insight_candidates: List[InsightCandidate]
    llm_report: Optional[Dict[str, Any]] = None
    completed_at: str
