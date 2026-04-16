// Dataset state machine
export type DatasetStatus =
  | 'uploaded'
  | 'profiling'
  | 'awaiting-mapping'
  | 'analyzing'
  | 'completed'
  | 'failed';

export type JobStatus = 'pending' | 'running' | 'completed' | 'failed';

// Semantic roles for columns
export type SemanticRole =
  | 'record_id'
  | 'case_id'
  | 'activity_name'
  | 'state'
  | 'status'
  | 'created_at'
  | 'updated_at'
  | 'resolved_at'
  | 'closed_at'
  | 'assignee'
  | 'assignment_group'
  | 'customer'
  | 'category'
  | 'subcategory'
  | 'priority'
  | 'sla_breach_flag'
  | 'satisfaction_score'
  | 'comment_text'
  | 'description'
  | 'duration'
  | 'channel'
  | 'source_system'
  | 'region'
  | 'queue'
  | 'unknown';

export type InferredColumnType =
  | 'integer'
  | 'float'
  | 'string'
  | 'boolean'
  | 'datetime'
  | 'date'
  | 'categorical'
  | 'free_text'
  | 'identifier'
  | 'unknown';

// Column profile produced by Python worker
export interface ColumnProfile {
  column_name: string;
  inferred_type: InferredColumnType;
  null_count: number;
  null_ratio: number;
  distinct_count: number;
  distinct_ratio: number;
  is_enum_like: boolean;
  is_free_text: boolean;
  sample_values: string[];
  min_value?: string;
  max_value?: string;
  mean_value?: number;
  median_value?: number;
  std_dev?: number;
  p25?: number;
  p75?: number;
  p95?: number;
  timestamp_parse_success_ratio?: number;
  top_values?: Array<{ value: string; count: number; pct: number }>;
}

// Semantic inference result
export interface SemanticInference {
  column_name: string;
  inferred_role: SemanticRole;
  confidence: number; // 0.0 - 1.0
  reason: string;
  sample_justification: string;
  alternative_roles: Array<{ role: SemanticRole; confidence: number }>;
}

// Profiling run result
export interface ProfilingResult {
  dataset_id: string;
  profiling_run_id: string;
  row_count: number;
  column_count: number;
  file_size_bytes: number;
  delimiter: string;
  encoding: string;
  has_header: boolean;
  columns: ColumnProfile[];
  semantic_inferences: SemanticInference[];
  process_readiness: ProcessReadinessScore;
  completed_at: string;
}

// Process readiness scores (0-100)
export interface ProcessReadinessScore {
  overall: number;
  timeline_quality: number;
  case_traceability: number;
  activity_clarity: number;
  actor_clarity: number;
  customer_segmentation: number;
  recommendation_confidence: number;
  warnings: string[];
}

// User mapping decisions
export interface MappingDecision {
  dataset_id: string;
  case_id_column?: string;
  activity_column?: string;
  created_at_column?: string;
  updated_at_column?: string;
  resolved_at_column?: string;
  closed_at_column?: string;
  assignee_column?: string;
  assignment_group_column?: string;
  customer_column?: string;
  satisfaction_column?: string;
  priority_column?: string;
  category_column?: string;
  subcategory_column?: string;
  status_column?: string;
  additional_dimensions?: Record<string, string>;
}

// Metric outputs
export interface VolumeOverTime {
  period: string;
  count: number;
  delta_pct?: number;
}

export interface WeekdayPattern {
  weekday: number; // 0=Mon, 6=Sun
  weekday_name: string;
  count: number;
  avg_count_per_week: number;
  relative_to_mean: number;
}

export interface HourlyPattern {
  hour: number;
  count: number;
  relative_to_mean: number;
}

export interface CategoryMetric {
  category: string;
  count: number;
  pct: number;
  avg_duration_minutes?: number;
  reopen_rate?: number;
}

export interface ActorMetric {
  actor: string;
  case_count: number;
  avg_duration_minutes?: number;
  median_duration_minutes?: number;
  p95_duration_minutes?: number;
  avg_satisfaction?: number;
  reassign_rate?: number;
}

export interface DurationMetrics {
  mean_minutes: number;
  median_minutes: number;
  p25_minutes: number;
  p75_minutes: number;
  p95_minutes: number;
  p99_minutes: number;
  std_dev_minutes: number;
}

export interface BacklogAgingBucket {
  age_bucket: string;
  count: number;
  pct: number;
}

// Insight candidate from programmatic engine
export type InsightType =
  | 'temporal_spike'
  | 'workload_imbalance'
  | 'customer_specific_delay'
  | 'assignee_performance_gap'
  | 'category_recurrence'
  | 'satisfaction_degradation'
  | 'self_service_opportunity'
  | 'routing_problem'
  | 'queue_bottleneck'
  | 'rework_loop_pattern'
  | 'outlier_case'
  | 'backlog_aging';

export interface InsightCandidate {
  insight_id: string;
  insight_type: InsightType;
  title: string;
  description_seed: string;
  support_count: number;
  impacted_population_pct: number;
  comparison_baseline?: string;
  effect_size: number;
  confidence: number;
  evidence_refs: Record<string, unknown>;
  recommended_action_seed: string;
  rank_score: number;
}

// Full metrics package from deterministic engine
export interface AnalysisMetrics {
  volume_over_time: VolumeOverTime[];
  weekday_patterns: WeekdayPattern[];
  hourly_patterns: HourlyPattern[];
  top_categories: CategoryMetric[];
  top_assignees: ActorMetric[];
  top_groups: ActorMetric[];
  duration_metrics: DurationMetrics;
  backlog_aging: BacklogAgingBucket[];
  reopen_rate_overall?: number;
  reassign_rate_overall?: number;
  sla_breach_rate?: number;
  avg_satisfaction?: number;
  outlier_cases: Array<{
    case_id: string;
    duration_minutes: number;
    z_score: number;
    category?: string;
    assignee?: string;
  }>;
}

// LLM evidence pack (sent to LLM)
export interface EvidencePack {
  dataset_summary: {
    row_count: number;
    column_count: number;
    date_range?: string;
    domains_detected: string[];
  };
  schema_profile: ColumnProfile[];
  semantic_inference: SemanticInference[];
  mapping_decisions: MappingDecision;
  metric_summary: AnalysisMetrics;
  ranked_insights: InsightCandidate[];
  output_language: string;
  target_audience: 'executive' | 'process_manager';
}

// LLM commentary output
export interface LLMReport {
  executive_summary: string;
  process_manager_summary: string;
  top_bottlenecks: Array<{
    title: string;
    description: string;
    severity: 'critical' | 'high' | 'medium' | 'low';
    recommendation: string;
  }>;
  hypotheses: Array<{
    hypothesis: string;
    supporting_evidence: string;
    confidence: 'high' | 'medium' | 'low';
  }>;
  recommendations: Array<{
    title: string;
    description: string;
    expected_impact: string;
    effort: 'low' | 'medium' | 'high';
    priority: number;
  }>;
  disclaimer: string;
  generated_at: string;
  model_used: string;
  is_mock: boolean;
}

// Enriched insight (candidate + LLM narrative)
export interface EnrichedInsight {
  insight_id: string;
  insight_type: InsightType;
  title: string;
  narrative: string;
  why_it_matters: string;
  evidence_metrics: Record<string, unknown>;
  impacted_segment: string;
  suggested_action: string;
  confidence: number;
  support_count: number;
  effect_size: number;
  rank_score: number;
}

// API response envelope
export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
  timestamp: string;
}

// Dataset entity
export interface Dataset {
  id: string;
  name: string;
  original_filename: string;
  file_size_bytes: number;
  status: DatasetStatus;
  row_count?: number;
  column_count?: number;
  created_at: string;
  updated_at: string;
  profiling_completed_at?: string;
  analysis_completed_at?: string;
  error_message?: string;
}

// Analysis run entity
export interface AnalysisRun {
  id: string;
  dataset_id: string;
  status: JobStatus;
  mapping_snapshot: MappingDecision;
  started_at: string;
  completed_at?: string;
  error_message?: string;
  duration_seconds?: number;
}

// Job entity
export interface Job {
  id: string;
  job_type: 'profiling' | 'analysis';
  dataset_id: string;
  analysis_run_id?: string;
  status: JobStatus;
  started_at: string;
  completed_at?: string;
  error_message?: string;
  progress?: number;
}
