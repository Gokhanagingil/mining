/**
 * Internal endpoints called by the Python analysis worker to report job completion.
 * Not exposed to the public.
 */
import { Controller, Post, Param, Body, Logger } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { DatasetEntity, AnalysisRunEntity, JobRunEntity } from '../common/entities';

interface JobCompleteBody {
  status: 'completed' | 'failed';
  result?: Record<string, any>;
  error?: string;
}

@Controller('internal')
export class InternalController {
  private readonly logger = new Logger(InternalController.name);

  constructor(
    @InjectRepository(DatasetEntity)
    private readonly datasetRepo: Repository<DatasetEntity>,
    @InjectRepository(AnalysisRunEntity)
    private readonly analysisRunRepo: Repository<AnalysisRunEntity>,
    @InjectRepository(JobRunEntity)
    private readonly jobRunRepo: Repository<JobRunEntity>,
  ) {}

  @Post('jobs/:jobId/complete')
  async jobComplete(
    @Param('jobId') jobId: string,
    @Body() body: JobCompleteBody,
  ) {
    const job = await this.jobRunRepo.findOne({ where: { id: jobId } });
    if (!job) {
      this.logger.warn(`Job ${jobId} not found`);
      return { ok: false };
    }

    const now = new Date();
    await this.jobRunRepo.update(jobId, {
      status: body.status,
      completedAt: now,
      ...(body.error !== undefined ? { errorMessage: body.error } : {}),
      ...(body.result !== undefined ? { resultPayload: body.result } : {}),
    });

    if (job.jobType === 'profiling') {
      await this.handleProfilingComplete(job, body);
    } else if (job.jobType === 'analysis') {
      await this.handleAnalysisComplete(job, body);
    }

    return { ok: true };
  }

  private async handleProfilingComplete(job: JobRunEntity, body: JobCompleteBody) {
    if (body.status === 'completed' && body.result) {
      const result = body.result;
      await this.datasetRepo.update(job.datasetId, {
        status: 'awaiting-mapping',
        rowCount: result.row_count,
        columnCount: result.column_count,
        profilingResult: result,
        profilingCompletedAt: new Date(),
      });
      this.logger.log(
        `Profiling completed for dataset ${job.datasetId}: ${result.row_count} rows, ${result.column_count} columns`,
      );
    } else {
      await this.datasetRepo.update(job.datasetId, {
        status: 'failed',
        errorMessage: body.error || 'Profiling failed',
      });
      this.logger.error(`Profiling failed for dataset ${job.datasetId}: ${body.error}`);
    }
  }

  private async handleAnalysisComplete(job: JobRunEntity, body: JobCompleteBody) {
    if (body.status === 'completed' && body.result) {
      const result = body.result;
      await this.analysisRunRepo.update(job.analysisRunId!, {
        status: 'completed',
        metricsResult: result.metrics,
        insightCandidates: result.insight_candidates,
        llmReport: result.llm_report,
        completedAt: new Date(),
      });
      await this.datasetRepo.update(job.datasetId, {
        status: 'completed',
        analysisCompletedAt: new Date(),
      });
      this.logger.log(
        `Analysis completed for dataset ${job.datasetId}, run ${job.analysisRunId}`,
      );
    } else {
      await this.analysisRunRepo.update(job.analysisRunId!, {
        status: 'failed',
        errorMessage: body.error || 'Analysis failed',
      });
      await this.datasetRepo.update(job.datasetId, {
        status: 'failed',
        errorMessage: body.error || 'Analysis failed',
      });
      this.logger.error(
        `Analysis failed for dataset ${job.datasetId}: ${body.error}`,
      );
    }
  }
}
