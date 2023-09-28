import { TestBed } from '@angular/core/testing';

import { QueueClientService } from './queue-client.service';

describe('QueueClientService', () => {
  let service: QueueClientService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(QueueClientService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
