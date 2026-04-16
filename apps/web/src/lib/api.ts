import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:3001';

export const api = axios.create({
  baseURL: API_BASE,
  timeout: 120000,
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    const message = err.response?.data?.error || err.message || 'Unknown error';
    return Promise.reject(new Error(message));
  }
);

// Datasets
export const datasetsApi = {
  upload: (file: File, onProgress?: (pct: number) => void) => {
    const form = new FormData();
    form.append('file', file);
    return api.post<ApiResponse<Dataset>>('/datasets/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (e) => {
        if (onProgress && e.total) {
          onProgress(Math.round((e.loaded / e.total) * 100));
        }
      },
    });
  },

  list: () => api.get<ApiResponse<Dataset[]>>('/datasets'),

  get: (id: string) => api.get<ApiResponse<Dataset>>(`/datasets/${id}`),

  startProfiling: (id: string) =>
    api.post<ApiResponse<JobRun>>(`/datasets/${id}/profile`),

  getProfile: (id: string) =>
    api.get<ApiResponse<ProfilingResult>>(`/datasets/${id}/profile`),

  updateMapping: (id: string, mapping: Record<string, any>) =>
    api.post<ApiResponse<Dataset>>(`/datasets/${id}/mapping`, mapping),

  startAnalysis: (id: string) =>
    api.post<ApiResponse<JobRun>>(`/datasets/${id}/analyze`),

  getResults: (id: string) =>
    api.get<ApiResponse<{ dataset: Dataset; latestRun: AnalysisRun | null }>>(
      `/datasets/${id}/results`
    ),

  getInsights: (id: string) =>
    api.get<ApiResponse<InsightCandidate[]>>(`/datasets/${id}/insights`),

  getRuns: (id: string) =>
    api.get<ApiResponse<AnalysisRun[]>>(`/datasets/${id}/runs`),
};

export const jobsApi = {
  list: (datasetId?: string) => {
    const params = datasetId ? { dataset_id: datasetId } : {};
    return api.get<ApiResponse<JobRun[]>>('/jobs', { params });
  },
};

// Types
export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
  timestamp: string;
}

export interface Dataset {
  id: string;
  name: string;
  originalFilename: string;
  fileSizeBytes: number;
  status: DatasetStatus;
  rowCount?: number;
  columnCount?: number;
  createdAt: string;
  updatedAt: string;
  profilingCompletedAt?: string;
  analysisCompletedAt?: string;
  errorMessage?: string;
  profilingResult?: ProfilingResult;
  mappingDecision?: MappingDecision;
  latestAnalysisRunId?: string;
}

export type DatasetStatus =
  | 'uploaded'
  | 'profiling'
  | 'awaiting-mapping'
  | 'analyzing'
  | 'completed'
  | 'failed';

export interface ColumnProfile {
  column_name: string;
  inferred_type: string;
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

export interface SemanticInference {
  column_name: string;
  inferred_role: string;
  confidence: number;
  reason: string;
  sample_justification: string;
  alternative_roles: Array<{ role: string; confidence: number }>;
}

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

export interface InsightCandidate {
  insight_id: string;
  insight_type: string;
  title: string;
  description_seed: string;
  support_count: number;
  impacted_population_pct: number;
  comparison_baseline?: string;
  effect_size: number;
  confidence: number;
  evidence_refs: Record<string, any>;
  recommended_action_seed: string;
  rank_score: number;
}

export interface AnalysisRun {
  id: string;
  datasetId: string;
  status: string;
  mappingSnapshot: MappingDecision;
  metricsResult?: Record<string, any>;
  insightCandidates?: InsightCandidate[];
  llmReport?: LLMReport;
  errorMessage?: string;
  durationSeconds?: number;
  startedAt: string;
  completedAt?: string;
}

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

export interface JobRun {
  id: string;
  jobType: string;
  datasetId: string;
  analysisRunId?: string;
  status: string;
  startedAt: string;
  completedAt?: string;
  errorMessage?: string;
  progress?: number;
}
