import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { environment } from '../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class DefinitionsClientService {

  constructor(private http: HttpClient) { }


  getDefinitions() {
    return this.perform('get', '/definitions');
  }

  getDefinition(name: string) {
    return this.perform('get', `/definitions/${name}`);
  }

  purgeDefinitionQueue(name: string) {
    return this.perform('PUT', `/definitions/${name}/purge_queue`);
  }

  perform(method: any, resource: any, data = {}) {
    const url = environment.apiUrl+resource;

    const httpOptions = {
      headers: new HttpHeaders({
        'Content-Type': 'application/json',
      })
    };
    return this.http.request(method, url, httpOptions);

  }
}