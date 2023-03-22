import { TestBed } from '@angular/core/testing';

import { DefinitionsClientService } from './definitions-client.service';

describe('DefinitionsClientService', () => {
  let service: DefinitionsClientService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(DefinitionsClientService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
