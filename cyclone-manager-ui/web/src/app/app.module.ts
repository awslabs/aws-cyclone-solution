import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { FormsModule } from '@angular/forms'
import { MatToolbarModule } from '@angular/material/toolbar'
import { MatButtonModule } from '@angular/material/button'
import { MatTableModule } from '@angular/material/table'
import { MatInputModule } from '@angular/material/input'
import { MatIconModule } from '@angular/material/icon'
import { MatPaginatorModule } from '@angular/material/paginator'
import { MatCardModule } from '@angular/material/card'
import { MatFormFieldModule } from '@angular/material/form-field'
import { MatDividerModule } from '@angular/material/divider'
import { MatSelectModule } from '@angular/material/select'
import { MatTabsModule } from '@angular/material/tabs'
import { MatChipsModule } from '@angular/material/chips'
import { MatProgressBarModule } from '@angular/material/progress-bar'
import { MatGridListModule } from '@angular/material/grid-list'
import { AppRoutingModule } from './app-routing.module';
import { AppComponent } from './app.component';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { HomeComponent } from './home/home.component';
import { HttpClientModule, HTTP_INTERCEPTORS } from '@angular/common/http';
import { RegionsComponent } from './regions/regions.component';
import { QueuesComponent } from './queues/queues.component';
import { QueueComponent } from './queue/queue.component';
import { MatSortModule } from '@angular/material/sort';
import { MatTooltipModule } from '@angular/material/tooltip';
import { ClustersComponent } from './clusters/clusters.component';
import { DefinitionsComponent } from './definitions/definitions.component';
import { DefinitionComponent } from './definition/definition.component';
import { JobsComponent } from './jobs/jobs.component';
import { ProgressInterceptor } from './progress.interceptor';


@NgModule({
  declarations: [
    AppComponent,
    HomeComponent,
    RegionsComponent,
    QueuesComponent,
    QueueComponent,
    ClustersComponent,
    DefinitionsComponent,
    DefinitionComponent,
    JobsComponent
  ],
  imports: [
    BrowserModule,
    FormsModule,
    AppRoutingModule,
    HttpClientModule,
    BrowserAnimationsModule,
    MatToolbarModule,
    MatSelectModule,
    MatButtonModule,
    MatIconModule,
    MatChipsModule,
    MatCardModule,
    MatTabsModule,
    MatGridListModule,
    MatDividerModule,
    MatTableModule,
    MatTooltipModule,
    MatFormFieldModule,
    MatPaginatorModule,
    MatInputModule,
    MatSortModule,
    MatProgressBarModule
  ],
  providers: [
    {
       provide: HTTP_INTERCEPTORS,
       useClass: ProgressInterceptor,
       multi: true,
    },
 ],
  bootstrap: [AppComponent]
})
export class AppModule { }
