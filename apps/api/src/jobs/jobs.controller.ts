import { Controller, Get, Query } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { JobRunEntity } from '../common/entities';
import { ok } from '../common/response';

@Controller('jobs')
export class JobsController {
  constructor(
    @InjectRepository(JobRunEntity)
    private readonly jobRepo: Repository<JobRunEntity>,
  ) {}

  @Get()
  async listJobs(@Query('dataset_id') datasetId?: string) {
    const where = datasetId ? { datasetId } : {};
    const jobs = await this.jobRepo.find({
      where,
      order: { startedAt: 'DESC' },
      take: 100,
    });
    return ok(jobs);
  }
}
