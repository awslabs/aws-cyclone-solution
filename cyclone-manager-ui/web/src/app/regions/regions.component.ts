import { Component } from '@angular/core';
import { RegionClientService } from '../region-client.service';

@Component({
  selector: 'app-regions',
  templateUrl: './regions.component.html',
  styleUrls: ['./regions.component.css']
})
export class RegionsComponent {
  regions: Array<any>;

  constructor(
    private regionsClient: RegionClientService
  ) {
    this.regions = [];
  }

  async ngOnInit() {
    this.regionsClient.getRegions().subscribe((regions: any) => {
      this.regions = regions;
    })
  }
}
