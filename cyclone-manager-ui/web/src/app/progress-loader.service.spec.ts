import { TestBed } from '@angular/core/testing';

import { ProgressLoaderService } from './progress-loader.service';

describe('ProgressLoaderService', () => {
  let service: ProgressLoaderService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(ProgressLoaderService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
