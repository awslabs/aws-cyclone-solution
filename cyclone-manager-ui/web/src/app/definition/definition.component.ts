import { Component } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { DefinitionsClientService } from '../definitions-client.service';

@Component({
  selector: 'app-definition',
  templateUrl: './definition.component.html',
  styleUrls: ['./definition.component.css']
})
export class DefinitionComponent {
  definition: any;

  constructor(
    private definitionsClient: DefinitionsClientService, private route: ActivatedRoute
  ) {
  }

  async ngOnInit() {
    this.definitionsClient.getDefinition(this.route.snapshot.params['name']).subscribe((definition: any) => {
      this.definition = definition
    })
  }
}