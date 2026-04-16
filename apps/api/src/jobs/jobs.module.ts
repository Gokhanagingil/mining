import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { JobsController } from './jobs.controller';
import { JobRunEntity } from '../common/entities';

@Module({
  imports: [TypeOrmModule.forFeature([JobRunEntity])],
  controllers: [JobsController],
})
export class JobsModule {}
