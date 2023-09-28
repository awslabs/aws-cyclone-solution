import { TestBed } from '@angular/core/testing';

import { JobsClientService } from './jobs-client.service';

describe('JobsClientService', () => {
  let service: JobsClientService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(JobsClientService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
