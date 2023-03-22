import { ComponentFixture, TestBed } from '@angular/core/testing';

import { QueuesComponent } from './queues.component';

describe('QueuesComponent', () => {
  let component: QueuesComponent;
  let fixture: ComponentFixture<QueuesComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ QueuesComponent ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(QueuesComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
