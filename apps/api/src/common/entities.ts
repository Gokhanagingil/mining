import {
  Entity,
  Column,
  PrimaryGeneratedColumn,
  CreateDateColumn,
  UpdateDateColumn,
  Index,
} from 'typeorm';

@Entity('datasets')
export class DatasetEntity {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Column()
  name: string;

  @Column({ name: 'original_filename' })
  originalFilename: string;

  @Column({ name: 'file_size_bytes', type: 'bigint', default: 0 })
  fileSizeBytes: number;

  @Column({ name: 'storage_path' })
  storagePath: string;

  @Column({ name: 'parquet_path', nullable: true })
  parquetPath: string;

  @Column({
    type: 'varchar',
    default: 'uploaded',
  })
  status: string;

  @Column({ name: 'row_count', nullable: true, type: 'bigint' })
  rowCount: number;

  @Column({ name: 'column_count', nullable: true })
  columnCount: number;

  @Column({ name: 'error_message', nullable: true, type: 'text' })
  errorMessage: string;

  @Column({ name: 'profiling_result', nullable: true, type: 'jsonb' })
  profilingResult: Record<string, any>;

  @Column({ name: 'mapping_decision', nullable: true, type: 'jsonb' })
  mappingDecision: Record<string, any>;

  @Column({ name: 'latest_analysis_run_id', nullable: true })
  latestAnalysisRunId: string;

  @CreateDateColumn({ name: 'created_at' })
  createdAt: Date;

  @UpdateDateColumn({ name: 'updated_at' })
  updatedAt: Date;

  @Column({ name: 'profiling_completed_at', nullable: true })
  profilingCompletedAt: Date;

  @Column({ name: 'analysis_completed_at', nullable: true })
  analysisCompletedAt: Date;
}

@Entity('analysis_runs')
export class AnalysisRunEntity {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Column({ name: 'dataset_id' })
  @Index()
  datasetId: string;

  @Column({ type: 'varchar', default: 'pending' })
  status: string;

  @Column({ name: 'mapping_snapshot', type: 'jsonb' })
  mappingSnapshot: Record<string, any>;

  @Column({ name: 'metrics_result', nullable: true, type: 'jsonb' })
  metricsResult: Record<string, any>;

  @Column({ name: 'insight_candidates', nullable: true, type: 'jsonb' })
  insightCandidates: Record<string, any>[];

  @Column({ name: 'llm_report', nullable: true, type: 'jsonb' })
  llmReport: Record<string, any>;

  @Column({ name: 'error_message', nullable: true, type: 'text' })
  errorMessage: string;

  @Column({ name: 'duration_seconds', nullable: true, type: 'float' })
  durationSeconds: number;

  @CreateDateColumn({ name: 'started_at' })
  startedAt: Date;

  @Column({ name: 'completed_at', nullable: true })
  completedAt: Date;
}

@Entity('job_runs')
export class JobRunEntity {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Column({ name: 'job_type' })
  jobType: string;

  @Column({ name: 'dataset_id' })
  @Index()
  datasetId: string;

  @Column({ name: 'analysis_run_id', nullable: true })
  analysisRunId: string;

  @Column({ type: 'varchar', default: 'pending' })
  status: string;

  @Column({ name: 'error_message', nullable: true, type: 'text' })
  errorMessage: string;

  @Column({ name: 'progress', nullable: true, type: 'int', default: 0 })
  progress: number;

  @Column({ name: 'result_payload', nullable: true, type: 'jsonb' })
  resultPayload: Record<string, any>;

  @CreateDateColumn({ name: 'started_at' })
  startedAt: Date;

  @Column({ name: 'completed_at', nullable: true })
  completedAt: Date;
}
