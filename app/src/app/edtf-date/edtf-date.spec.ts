import { TestBed } from '@angular/core/testing';
import { Component } from '@angular/core';
import { EdtfDateComponent } from './edtf-date';

// 用一個小型 host 元件測試，而不是直接對 EdtfDateComponent 呼叫 setInput()——
// 這個元件唯一的 input 是 required，透過 host 元件的 template binding 測試更貼近
// 真實使用方式（其他有 required input 的元件在這個專案裡也是這樣測，例如
// TimeScrubberComponent 沒有 required input 所以不用，但 pattern 一致）。
@Component({
  standalone: true,
  imports: [EdtfDateComponent],
  template: `<app-edtf-date [value]="value" />`,
})
class HostComponent {
  value = '0208';
}

describe('EdtfDateComponent', () => {
  function render(value: string): { fixture: ReturnType<typeof TestBed.createComponent<HostComponent>>; text: () => string } {
    const fixture = TestBed.createComponent(HostComponent);
    fixture.componentInstance.value = value;
    fixture.detectChanges();
    return {
      fixture,
      text: () => (fixture.nativeElement.querySelector('.edtf-date') as HTMLElement).textContent!.replace(/\s+/g, ' ').trim(),
    };
  }

  it('年精度日期只顯示到年', () => {
    const { text } = render('0208');
    expect(text()).toBe('西元 208 年');
  });

  it('日精度日期顯示到日，不省略月/日', () => {
    const { text } = render('0208-10-15');
    expect(text()).toBe('西元 208 年 10 月 15 日');
  });

  it('不確定標記顯示「推測年份」提示，且跟主要日期文字分開放在獨立的 span', () => {
    const { fixture } = render('1046?');

    const main = fixture.nativeElement.querySelector('.edtf-date')!.childNodes[0].textContent.trim();
    const qualifier = fixture.nativeElement.querySelector('.edtf-date-qualifier')!.textContent.trim();
    expect(main).toBe('西元 1046 年');
    expect(qualifier).toBe('（推測年份）');
  });

  it('沒有不確定標記時，不渲染 qualifier span', () => {
    const { fixture } = render('0208');
    expect(fixture.nativeElement.querySelector('.edtf-date-qualifier')).toBeNull();
  });

  it('無法解析的字串直接顯示原始字串，不整個消失', () => {
    const { text } = render('garbled-date-string');
    expect(text()).toBe('garbled-date-string');
  });

  it('西元前年份正確顯示', () => {
    const { text } = render('-0099');
    expect(text()).toBe('西元前 100 年');
  });
});
