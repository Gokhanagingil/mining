import { Injectable, Logger } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import * as fs from 'fs';
import * as path from 'path';

@Injectable()
export class StorageService {
  private readonly logger = new Logger(StorageService.name);
  private readonly storagePath: string;
  private readonly parquetPath: string;

  constructor(private config: ConfigService) {
    this.storagePath = config.get('STORAGE_PATH', '/data/storage');
    this.parquetPath = config.get('PARQUET_PATH', '/data/parquet');
    this.ensureDirectories();
  }

  private ensureDirectories() {
    [this.storagePath, this.parquetPath].forEach((dir) => {
      if (!fs.existsSync(dir)) {
        fs.mkdirSync(dir, { recursive: true });
        this.logger.log(`Created directory: ${dir}`);
      }
    });
  }

  getUploadPath(datasetId: string, filename: string): string {
    const dir = path.join(this.storagePath, datasetId);
    fs.mkdirSync(dir, { recursive: true });
    return path.join(dir, filename);
  }

  getParquetPath(datasetId: string): string {
    return path.join(this.parquetPath, datasetId, 'data.parquet');
  }

  getStorageBasePath(): string {
    return this.storagePath;
  }

  fileExists(filePath: string): boolean {
    return fs.existsSync(filePath);
  }

  deleteFile(filePath: string): void {
    if (fs.existsSync(filePath)) {
      fs.unlinkSync(filePath);
    }
  }

  async saveUploadedFile(
    buffer: Buffer,
    datasetId: string,
    originalFilename: string,
  ): Promise<string> {
    const safeFilename = originalFilename.replace(/[^a-zA-Z0-9._-]/g, '_');
    const filePath = this.getUploadPath(datasetId, safeFilename);
    fs.writeFileSync(filePath, buffer);
    return filePath;
  }
}
