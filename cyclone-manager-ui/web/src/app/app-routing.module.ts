import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { ClustersComponent } from './clusters/clusters.component';
import { DefinitionComponent } from './definition/definition.component';
import { DefinitionsComponent } from './definitions/definitions.component';
import { HomeComponent } from './home/home.component';
import { JobsComponent } from './jobs/jobs.component';
import { QueueComponent } from './queue/queue.component';
import { QueuesComponent } from './queues/queues.component';
import { RegionsComponent } from './regions/regions.component';

const routes: Routes = [
  {
    path: '',
    component: HomeComponent,
  },
  {
    path: 'jobs',
    component: JobsComponent,
  },
  {
    path: 'regions',
    component: RegionsComponent,
  },
  {
    path: 'clusters',
    component: ClustersComponent,
  },
  {
    path: 'definitions',
    component: DefinitionsComponent,
  },
  {
    path: 'definitions/:name',
    component: DefinitionComponent,
  },
  {
    path: 'queues',
    component: QueuesComponent,
  },
  {
    path: 'queues/:name',
    component: QueueComponent
  },
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule]
})


export class AppRoutingModule { }
