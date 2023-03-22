import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { environment } from '../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class JobsClientService {

  constructor(private http: HttpClient) { }

  getJobs() {
    return this.perform('get', '/jobs');
  }

  getJob(name: string) {
    return this.perform('get', `/jobs/${name}`);
  }

  perform(method: any, resource: any, data = {}) {
    const url = environment.apiUrl + resource;

    const httpOptions = {
      headers: new HttpHeaders({
        'Content-Type': 'application/json',
      })
    };
    return this.http.request(method, url, httpOptions);

  }
}