import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { InternalController } from './internal.controller';
import {
  DatasetEntity,
  AnalysisRunEntity,
  JobRunEntity,
} from '../common/entities';

@Module({
  imports: [
    TypeOrmModule.forFeature([DatasetEntity, AnalysisRunEntity, JobRunEntity]),
  ],
  controllers: [InternalController],
})
export class InternalModule {}
