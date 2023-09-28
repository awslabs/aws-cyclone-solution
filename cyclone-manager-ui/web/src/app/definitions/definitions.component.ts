import { Component, ViewChild } from '@angular/core';
import { MatPaginator } from '@angular/material/paginator';
import { MatSort, MatSortable } from '@angular/material/sort';
import { MatTableDataSource } from '@angular/material/table';
import { ActivatedRoute } from '@angular/router';
import { DefinitionsClientService } from '../definitions-client.service';

@Component({
  selector: 'app-definitions',
  templateUrl: './definitions.component.html',
  styleUrls: ['./definitions.component.css']
})
export class DefinitionsComponent {
  definitions: MatTableDataSource<any>;
  displayedColumns: string[] = ['name', 'vcpus', 'gpu_count', 'memory_limit_mib', 'pending_sqs', 'status', 'actions'];

  @ViewChild(MatPaginator) paginator: MatPaginator;
  @ViewChild(MatSort) sort: MatSort;

  constructor(
    private definitionsClient: DefinitionsClientService
  ) {
    this.definitions = new MatTableDataSource<any>;
  }

  applyFilter(event: Event) {
    const filterValue = (event.target as HTMLInputElement).value;
    this.definitions.filter = filterValue.trim().toLowerCase();

    if (this.definitions.paginator) {
      this.definitions.paginator.firstPage();
    }
  }

  purgeDefinitionQueue(name: string) {
    console.log('Purging queue ' + name);
    this.definitionsClient.purgeDefinitionQueue(name).subscribe(() => {
      this.getData()
    })
  }

  getData() {
    this.definitionsClient.getDefinitions().subscribe((definitions: any) => {
      this.definitions = new MatTableDataSource(definitions)
      this.definitions.paginator = this.paginator;
      this.sort.sort(({ id: 'name', start: 'desc' }) as MatSortable);
      this.definitions.sort = this.sort;
    })
  }

  async ngOnInit() {
    this.getData()
  }
}