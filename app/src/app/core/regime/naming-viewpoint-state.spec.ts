import { TestBed } from '@angular/core/testing';
import { NamingViewpointState } from './naming-viewpoint-state';

describe('NamingViewpointState', () => {
  let service: NamingViewpointState;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(NamingViewpointState);
  });

  it('預設是 null（全球客觀視角）', () => {
    expect(service.observerRegimeId()).toBeNull();
  });

  it('setObserver() 寫入指定的觀察政權 id', () => {
    service.setObserver('r-shuhan');
    expect(service.observerRegimeId()).toBe('r-shuhan');
  });

  it('setObserver(null) 切回全球客觀視角', () => {
    service.setObserver('r-shuhan');
    service.setObserver(null);
    expect(service.observerRegimeId()).toBeNull();
  });
});
