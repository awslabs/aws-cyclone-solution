import { Component, ViewChild } from '@angular/core';
import { JobsClientService } from '../jobs-client.service';
import { MatPaginator } from '@angular/material/paginator';
import { MatSort, MatSortable } from '@angular/material/sort';
import { MatTableDataSource } from '@angular/material/table';

@Component({
  selector: 'app-jobs',
  templateUrl: './jobs.component.html',
  styleUrls: ['./jobs.component.css']
})
export class JobsComponent {
  jobs: MatTableDataSource<any>;
  useast1: Number;
  useast2: Number;
  uswest1: Number;
  uswest2: Number;
  displayedColumns: string[] = ['id', 'aws_batch_job_id', 'jobdefinition', 'jobqueue', 'region', 'hostname', 'status', 'actions'];

  @ViewChild(MatPaginator) paginator: MatPaginator;
  @ViewChild(MatSort) sort: MatSort;

  constructor(
    private jobsClient: JobsClientService
  ) {
    this.jobs = new MatTableDataSource<any>;
    this.useast1 = 0;
    this.useast2 = 0;
    this.uswest1 = 0;
    this.uswest2 = 0;
  }


  async ngOnInit() {
    this.getData();
  }

  getData() {
    this.jobsClient.getJobs().subscribe((jobs: any) => {
      this.jobs = new MatTableDataSource(jobs)
      this.jobs.paginator = this.paginator;
      this.sort.sort(({ id: 'id', start: 'desc' }) as MatSortable);
      this.jobs.sort = this.sort;
      this.useast1 = this.jobs.data.filter(member => member.region == "us-east-1").length
      this.useast2 = this.jobs.data.filter(member => member.region == "us-east-2").length
      this.uswest1 = this.jobs.data.filter(member => member.region == "us-west-1").length
      this.uswest2 = this.jobs.data.filter(member => member.region == "us-west-2").length
    })
  }

  applyFilter(event: Event) {
    const filterValue = (event.target as HTMLInputElement).value;
    this.jobs.filter = filterValue.trim().toLowerCase();

    if (this.jobs.paginator) {
      this.jobs.paginator.firstPage();
    }
  }
}