import { Component } from '@angular/core';
import { QueueClientService } from '../queue-client.service';

@Component({
  selector: 'app-queues',
  templateUrl: './queues.component.html',
  styleUrls: ['./queues.component.css']
})
export class QueuesComponent {
  queues: Array<any>;

  constructor(
    private queueClient: QueueClientService
  ) {
    this.queues = [];
  }

  async ngOnInit() {
    this.queueClient.getQueues().subscribe((queues: any) => {
      this.queues = queues;
    })
  }
}