import { Module } from '@nestjs/common';
import { ConfigModule, ConfigService } from '@nestjs/config';
import { TypeOrmModule } from '@nestjs/typeorm';
import { HttpModule } from '@nestjs/axios';
import { DatasetsModule } from './datasets/datasets.module';
import { JobsModule } from './jobs/jobs.module';
import { InternalModule } from './internal/internal.module';
import {
  DatasetEntity,
  AnalysisRunEntity,
  JobRunEntity,
} from './common/entities';
import { AppController } from './app.controller';
import { AppService } from './app.service';

@Module({
  imports: [
    ConfigModule.forRoot({
      isGlobal: true,
      envFilePath: ['.env', '../../.env'],
    }),
    TypeOrmModule.forRootAsync({
      imports: [ConfigModule],
      useFactory: (config: ConfigService) => ({
        type: 'postgres',
        url: config.get(
          'DATABASE_URL',
          'postgresql://mining:mining@postgres:5432/mining',
        ),
        entities: [DatasetEntity, AnalysisRunEntity, JobRunEntity],
        synchronize: true, // auto-create tables; use migrations in production
        logging: config.get('NODE_ENV') === 'development',
        retryAttempts: 10,
        retryDelay: 3000,
      }),
      inject: [ConfigService],
    }),
    HttpModule,
    DatasetsModule,
    JobsModule,
    InternalModule,
  ],
  controllers: [AppController],
  providers: [AppService],
})
export class AppModule {}
