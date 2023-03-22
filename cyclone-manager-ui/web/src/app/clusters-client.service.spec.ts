import { TestBed } from '@angular/core/testing';

import { ClustersClientService } from './clusters-client.service';

describe('ClustersClientService', () => {
  let service: ClustersClientService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(ClustersClientService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
