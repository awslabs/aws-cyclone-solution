import { Component } from '@angular/core';
import { Subject } from 'rxjs';
import { ProgressLoaderService } from './progress-loader.service';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css']
})
export class AppComponent {
  appName = 'Cyclone Manager';
  isLoading: Subject<boolean> = this.progressService.isLoading;

  constructor(private progressService: ProgressLoaderService) {
  }
}
