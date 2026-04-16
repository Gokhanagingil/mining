import {
  Controller,
  Get,
  Post,
  Param,
  Body,
  UploadedFile,
  UseInterceptors,
  HttpException,
  HttpStatus,
  Logger,
} from '@nestjs/common';
import { FileInterceptor } from '@nestjs/platform-express';
import { memoryStorage } from 'multer';
import { DatasetsService } from './datasets.service';
import { ok, fail } from '../common/response';

@Controller('datasets')
export class DatasetsController {
  private readonly logger = new Logger(DatasetsController.name);

  constructor(private readonly service: DatasetsService) {}

  @Post('upload')
  @UseInterceptors(
    FileInterceptor('file', {
      storage: memoryStorage(),
      limits: { fileSize: 600 * 1024 * 1024 }, // 600MB max in memory
    }),
  )
  async uploadDataset(@UploadedFile() file: Express.Multer.File) {
    if (!file) {
      throw new HttpException(fail('No file uploaded'), HttpStatus.BAD_REQUEST);
    }

    try {
      const dataset = await this.service.createDataset(
        file.buffer,
        file.originalname,
        file.size,
      );
      return ok(dataset, 'Dataset uploaded successfully');
    } catch (err) {
      this.logger.error(`Upload failed: ${err.message}`);
      throw new HttpException(fail(err.message), HttpStatus.BAD_REQUEST);
    }
  }

  @Get()
  async listDatasets() {
    const datasets = await this.service.findAll();
    return ok(datasets);
  }

  @Get(':id')
  async getDataset(@Param('id') id: string) {
    try {
      const dataset = await this.service.findOne(id);
      return ok(dataset);
    } catch (err) {
      throw new HttpException(fail(err.message), HttpStatus.NOT_FOUND);
    }
  }

  @Post(':id/profile')
  async startProfiling(@Param('id') id: string) {
    try {
      const job = await this.service.startProfiling(id);
      return ok(job, 'Profiling started');
    } catch (err) {
      this.logger.error(`Profiling failed: ${err.message}`);
      throw new HttpException(
        fail(err.message),
        err.status || HttpStatus.INTERNAL_SERVER_ERROR,
      );
    }
  }

  @Get(':id/profile')
  async getProfile(@Param('id') id: string) {
    const dataset = await this.service.findOne(id);
    if (!dataset.profilingResult) {
      throw new HttpException(
        fail('Profiling not yet complete'),
        HttpStatus.NOT_FOUND,
      );
    }
    return ok(dataset.profilingResult);
  }

  @Post(':id/mapping')
  async updateMapping(
    @Param('id') id: string,
    @Body() body: Record<string, any>,
  ) {
    try {
      const dataset = await this.service.updateMapping(id, body);
      return ok(dataset, 'Mapping updated successfully');
    } catch (err) {
      throw new HttpException(
        fail(err.message),
        err.status || HttpStatus.BAD_REQUEST,
      );
    }
  }

  @Post(':id/analyze')
  async startAnalysis(@Param('id') id: string) {
    try {
      const job = await this.service.startAnalysis(id);
      return ok(job, 'Analysis started');
    } catch (err) {
      this.logger.error(`Analysis failed: ${err.message}`);
      throw new HttpException(
        fail(err.message),
        err.status || HttpStatus.BAD_REQUEST,
      );
    }
  }

  @Get(':id/results')
  async getResults(@Param('id') id: string) {
    const { dataset, latestRun } = await this.service.getResults(id);
    return ok({ dataset, latestRun });
  }

  @Get(':id/insights')
  async getInsights(@Param('id') id: string) {
    const insights = await this.service.getInsights(id);
    return ok(insights);
  }

  @Get(':id/runs')
  async getAnalysisRuns(@Param('id') id: string) {
    const runs = await this.service.getAnalysisRuns(id);
    return ok(runs);
  }
}
