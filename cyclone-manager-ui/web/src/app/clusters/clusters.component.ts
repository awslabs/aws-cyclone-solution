import { Component } from '@angular/core';
import { ClustersClientService } from '../clusters-client.service';

@Component({
  selector: 'app-clusters',
  templateUrl: './clusters.component.html',
  styleUrls: ['./clusters.component.css']
})
export class ClustersComponent {
  clusters: Array<any>;
  
  constructor(
    private clustersClient: ClustersClientService
  ) {
    this.clusters = [];
  }

  async ngOnInit() {
    this.clustersClient.getClusters().subscribe((clusters: any) => {
      this.clusters = clusters;
    })
  }
}