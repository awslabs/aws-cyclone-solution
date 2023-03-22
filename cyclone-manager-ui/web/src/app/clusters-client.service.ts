import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { environment } from '../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class ClustersClientService {

  constructor(private http: HttpClient) { }


  getClusters() {
    return this.perform('get', '/clusters');
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