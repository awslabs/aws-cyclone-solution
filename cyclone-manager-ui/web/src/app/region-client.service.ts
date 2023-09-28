import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { environment } from '../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class RegionClientService {

  constructor(private http: HttpClient) { }

  getRegions() {
    return this.perform('get', '/regions');
  }

  perform(method: any, resource: any, data = {}) {
    const url = environment.apiUrl+resource;

    const httpOptions = {
      headers: new HttpHeaders({
        'Content-Type': 'application/json',
      })
    };
    return this.http.request(method, url,  httpOptions);

  }
}


