import { Component, ViewChild } from '@angular/core';
import { QueueClientService } from '../queue-client.service';
import { ActivatedRoute, Router } from '@angular/router';
import { MatPaginator } from '@angular/material/paginator';
import { MatSort, MatSortable } from '@angular/material/sort';
import { MatTableDataSource } from '@angular/material/table';

@Component({
  selector: 'app-queue',
  templateUrl: './queue.component.html',
  styleUrls: ['./queue.component.css']
})
export class QueueComponent {
  queue: MatTableDataSource<any>;
  queueName: string;
  displayedColumns: string[] = ['tcreated', 'jobname', 'status', 'terror', 'retriesavailable'];

  @ViewChild(MatPaginator) paginator: MatPaginator;
  @ViewChild(MatSort) sort: MatSort;

  constructor(
    private queueClient: QueueClientService, private route: ActivatedRoute
  ) {
    this.queue = new MatTableDataSource<any>;
    this.queueName = '';
  }

  applyFilter(event: Event) {
    const filterValue = (event.target as HTMLInputElement).value;
    this.queue.filter = filterValue.trim().toLowerCase();

    if (this.queue.paginator) {
      this.queue.paginator.firstPage();
    }
  }

  getQueue() {
    this.queueClient.getQueue(this.queueName).subscribe((queue: any) => {
      this.queue = new MatTableDataSource(queue)
      this.queue.paginator = this.paginator;
      this.sort.sort(({ id: 'tcreated', start: 'desc' }) as MatSortable);
      this.queue.sort = this.sort;
    })
  }


  async ngOnInit() {
    this.queueName = this.route.snapshot.params['name'];
    this.getQueue();
  }
}