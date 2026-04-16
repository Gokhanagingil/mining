import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { HttpModule } from '@nestjs/axios';
import { DatasetsController } from './datasets.controller';
import { DatasetsService } from './datasets.service';
import { DatasetEntity, AnalysisRunEntity, JobRunEntity } from '../common/entities';
import { StorageService } from '../storage/storage.service';

@Module({
  imports: [
    TypeOrmModule.forFeature([DatasetEntity, AnalysisRunEntity, JobRunEntity]),
    HttpModule,
  ],
  controllers: [DatasetsController],
  providers: [DatasetsService, StorageService],
  exports: [DatasetsService],
})
export class DatasetsModule {}
