import { Injectable } from '@angular/core';
import {
  HttpRequest,
  HttpHandler,
  HttpEvent,
  HttpInterceptor
} from '@angular/common/http';
import { finalize, Observable } from 'rxjs';
import { ProgressLoaderService } from './progress-loader.service';

@Injectable()
export class ProgressInterceptor implements HttpInterceptor {

  constructor(private progressService: ProgressLoaderService) {
  }

  intercept(request: HttpRequest<unknown>, next: HttpHandler): Observable<HttpEvent<unknown>> {
     this.progressService.show();

     return next.handle(request).pipe(
           finalize(() => this.progressService.hide()),
     );
  }
}