import { TestBed } from '@angular/core/testing';
import { TimeScrubberComponent } from './time-scrubber';
import { TimelineState } from '../core/time/timeline-state';

describe('TimeScrubberComponent', () => {
  // TimelineState 是 providedIn: 'root' 的單例——不 reset 的話，前一個 it() 改過的
  // year 值會留到下一個 it()，測試結果會互相影響（跟 map.spec.ts 需要
  // resetTestingModule() 是同一個道理）。
  beforeEach(() => {
    TestBed.resetTestingModule();
  });

  it('顯示 TimelineState 目前的年份', () => {
    const fixture = TestBed.createComponent(TimeScrubberComponent);
    fixture.detectChanges();

    const yearText = fixture.nativeElement.querySelector('.time-scrubber-year').textContent;
    expect(yearText).toContain(String(TimelineState.DEFAULT_YEAR));
  });

  it('拖動 range input 會更新 TimelineState.year', () => {
    const fixture = TestBed.createComponent(TimeScrubberComponent);
    fixture.detectChanges();
    const timeline = TestBed.inject(TimelineState);

    const input: HTMLInputElement = fixture.nativeElement.querySelector('.time-scrubber-input');
    input.value = '150';
    input.dispatchEvent(new Event('input'));
    fixture.detectChanges();

    expect(timeline.year()).toBe(150);
    expect(fixture.nativeElement.querySelector('.time-scrubber-year').textContent).toContain('150');
  });

  it('range input 的上下限對到 TimelineState 定義的範圍', () => {
    const fixture = TestBed.createComponent(TimeScrubberComponent);
    fixture.detectChanges();

    const input: HTMLInputElement = fixture.nativeElement.querySelector('.time-scrubber-input');
    expect(input.min).toBe(String(TimelineState.MIN_YEAR));
    expect(input.max).toBe(String(TimelineState.MAX_YEAR));
  });
});
