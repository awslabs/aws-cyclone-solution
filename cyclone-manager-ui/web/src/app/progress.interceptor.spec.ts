import { TestBed } from '@angular/core/testing';

import { ProgressInterceptor } from './progress.interceptor';

describe('ProgressInterceptor', () => {
  beforeEach(() => TestBed.configureTestingModule({
    providers: [
      ProgressInterceptor
      ]
  }));

  it('should be created', () => {
    const interceptor: ProgressInterceptor = TestBed.inject(ProgressInterceptor);
    expect(interceptor).toBeTruthy();
  });
});
