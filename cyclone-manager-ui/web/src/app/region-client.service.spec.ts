import { TestBed } from '@angular/core/testing';

import { RegionClientService } from './region-client.service';

describe('RegionClientService', () => {
  let service: RegionClientService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(RegionClientService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
