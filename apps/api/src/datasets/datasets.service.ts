import {
  Injectable,
  Logger,
  NotFoundException,
  BadRequestException,
} from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { ConfigService } from '@nestjs/config';
import { v4 as uuidv4 } from 'uuid';
import { HttpService } from '@nestjs/axios';
import { firstValueFrom } from 'rxjs';
import {
  DatasetEntity,
  AnalysisRunEntity,
  JobRunEntity,
} from '../common/entities';
import { StorageService } from '../storage/storage.service';

const WORKER_URL_KEY = 'WORKER_URL';
const DEFAULT_WORKER_URL = 'http://worker:8000';

@Injectable()
export class DatasetsService {
  private readonly logger = new Logger(DatasetsService.name);

  constructor(
    @InjectRepository(DatasetEntity)
    private readonly datasetRepo: Repository<DatasetEntity>,
    @InjectRepository(AnalysisRunEntity)
    private readonly analysisRunRepo: Repository<AnalysisRunEntity>,
    @InjectRepository(JobRunEntity)
    private readonly jobRunRepo: Repository<JobRunEntity>,
    private readonly storage: StorageService,
    private readonly config: ConfigService,
    private readonly http: HttpService,
  ) {}

  private get workerUrl(): string {
    return this.config.get(WORKER_URL_KEY, DEFAULT_WORKER_URL);
  }

  async createDataset(
    buffer: Buffer,
    originalFilename: string,
    fileSizeBytes: number,
  ): Promise<DatasetEntity> {
    if (
      !originalFilename.toLowerCase().endsWith('.csv') &&
      !originalFilename.toLowerCase().endsWith('.csv.gz')
    ) {
      throw new BadRequestException('Only CSV files are supported');
    }

    const maxMb = this.config.get<number>('MAX_FILE_SIZE_MB', 500);
    if (fileSizeBytes > maxMb * 1024 * 1024) {
      throw new BadRequestException(`File size exceeds ${maxMb}MB limit`);
    }

    const id = uuidv4();
    const storagePath = this.storage.saveUploadedFile(
      buffer,
      id,
      originalFilename,
    );

    const dataset = this.datasetRepo.create({
      id,
      name: originalFilename.replace(/\.[^.]+$/, ''),
      originalFilename,
      fileSizeBytes,
      storagePath,
      status: 'uploaded',
    });

    return this.datasetRepo.save(dataset);
  }

  async findAll(): Promise<DatasetEntity[]> {
    return this.datasetRepo.find({
      order: { createdAt: 'DESC' },
    });
  }

  async findOne(id: string): Promise<DatasetEntity> {
    const dataset = await this.datasetRepo.findOne({ where: { id } });
    if (!dataset) throw new NotFoundException(`Dataset ${id} not found`);
    return dataset;
  }

  async startProfiling(datasetId: string): Promise<JobRunEntity> {
    const dataset = await this.findOne(datasetId);

    if (!['uploaded', 'failed'].includes(dataset.status)) {
      throw new BadRequestException(
        `Cannot profile dataset in status '${dataset.status}'`,
      );
    }

    const jobId = uuidv4();
    const job = this.jobRunRepo.create({
      id: jobId,
      jobType: 'profiling',
      datasetId,
      status: 'pending',
      progress: 0,
    });
    await this.jobRunRepo.save(job);

    // Update dataset status
    await this.datasetRepo.update(datasetId, { status: 'profiling' });

    // Trigger worker (fire and forget)
    void this.triggerProfiling(dataset, jobId).catch((err) => {
      this.logger.error(`Failed to trigger profiling: ${err.message}`);
    });

    return job;
  }

  private async triggerProfiling(dataset: DatasetEntity, jobId: string) {
    const parquetPath = this.storage.getParquetPath(dataset.id);

    try {
      await firstValueFrom(
        this.http.post(`${this.workerUrl}/profiling/run`, {
          dataset_id: dataset.id,
          file_path: dataset.storagePath,
          parquet_output_path: parquetPath,
          job_id: jobId,
        }),
      );
      this.logger.log(
        `Profiling triggered for dataset ${dataset.id}, job ${jobId}`,
      );
    } catch (err) {
      this.logger.error(`Worker call failed for profiling: ${err.message}`);
      await this.jobRunRepo.update(jobId, {
        status: 'failed',
        errorMessage: err.message,
        completedAt: new Date(),
      });
      await this.datasetRepo.update(dataset.id, {
        status: 'failed',
        errorMessage: `Profiling trigger failed: ${err.message}`,
      });
    }
  }

  async updateMapping(
    datasetId: string,
    mappingDecision: Record<string, any>,
  ): Promise<DatasetEntity> {
    const dataset = await this.findOne(datasetId);

    if (!['awaiting-mapping', 'completed', 'failed'].includes(dataset.status)) {
      throw new BadRequestException(
        `Cannot update mapping for dataset in status '${dataset.status}'`,
      );
    }

    await this.datasetRepo
      .createQueryBuilder()
      .update()
      .set({
        mappingDecision: () =>
          `'${JSON.stringify({ ...mappingDecision, dataset_id: datasetId })}'::jsonb`,
        status: 'awaiting-mapping' as any,
      })
      .where('id = :id', { id: datasetId })
      .execute();

    return this.findOne(datasetId);
  }

  async startAnalysis(datasetId: string): Promise<JobRunEntity> {
    const dataset = await this.findOne(datasetId);

    if (!['awaiting-mapping', 'completed'].includes(dataset.status)) {
      throw new BadRequestException(
        `Cannot analyze dataset in status '${dataset.status}'`,
      );
    }

    if (!dataset.mappingDecision) {
      throw new BadRequestException('Mapping must be set before analysis');
    }

    const parquetPath = this.storage.getParquetPath(dataset.id);
    if (!this.storage.fileExists(parquetPath)) {
      throw new BadRequestException(
        'Parquet file not found. Run profiling first.',
      );
    }

    const analysisRunId = uuidv4();
    const run = this.analysisRunRepo.create({
      id: analysisRunId,
      datasetId,
      status: 'running',
      mappingSnapshot: dataset.mappingDecision,
    });
    await this.analysisRunRepo.save(run);

    const jobId = uuidv4();
    const job = this.jobRunRepo.create({
      id: jobId,
      jobType: 'analysis',
      datasetId,
      analysisRunId,
      status: 'pending',
      progress: 0,
    });
    await this.jobRunRepo.save(job);

    await this.datasetRepo.update(datasetId, {
      status: 'analyzing',
      latestAnalysisRunId: analysisRunId,
    });

    void this.triggerAnalysis(dataset, run, jobId).catch((err) => {
      this.logger.error(`Failed to trigger analysis: ${err.message}`);
    });

    return job;
  }

  private async triggerAnalysis(
    dataset: DatasetEntity,
    run: AnalysisRunEntity,
    jobId: string,
  ) {
    const parquetPath = this.storage.getParquetPath(dataset.id);

    try {
      await firstValueFrom(
        this.http.post(`${this.workerUrl}/analysis/run`, {
          dataset_id: dataset.id,
          analysis_run_id: run.id,
          parquet_path: parquetPath,
          mapping: dataset.mappingDecision,
          job_id: jobId,
        }),
      );
      this.logger.log(
        `Analysis triggered for dataset ${dataset.id}, run ${run.id}`,
      );
    } catch (err) {
      this.logger.error(`Worker call failed for analysis: ${err.message}`);
      await this.jobRunRepo.update(jobId, {
        status: 'failed',
        errorMessage: err.message,
        completedAt: new Date(),
      });
      await this.analysisRunRepo.update(run.id, {
        status: 'failed',
        errorMessage: `Analysis trigger failed: ${err.message}`,
      });
      await this.datasetRepo.update(dataset.id, {
        status: 'failed',
        errorMessage: `Analysis trigger failed: ${err.message}`,
      });
    }
  }

  async getResults(datasetId: string): Promise<{
    dataset: DatasetEntity;
    latestRun: AnalysisRunEntity | null;
  }> {
    const dataset = await this.findOne(datasetId);
    let latestRun: AnalysisRunEntity | null = null;

    if (dataset.latestAnalysisRunId) {
      latestRun = await this.analysisRunRepo.findOne({
        where: { id: dataset.latestAnalysisRunId },
      });
    }

    return { dataset, latestRun };
  }

  async getInsights(datasetId: string): Promise<Record<string, any>[]> {
    const dataset = await this.findOne(datasetId);
    if (!dataset.latestAnalysisRunId) return [];

    const run = await this.analysisRunRepo.findOne({
      where: { id: dataset.latestAnalysisRunId },
    });

    return run?.insightCandidates || [];
  }

  async getAnalysisRuns(datasetId: string): Promise<AnalysisRunEntity[]> {
    return this.analysisRunRepo.find({
      where: { datasetId },
      order: { startedAt: 'DESC' },
    });
  }
}
