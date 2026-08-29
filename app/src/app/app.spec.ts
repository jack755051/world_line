import { TestBed } from '@angular/core/testing';
import { App } from './app';

describe('App', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [App],
    })
      .compileComponents();
  });

  it('should create the app', () => {
    const fixture = TestBed.createComponent(App);
    const app = fixture.componentInstance;
    expect(app).toBeTruthy();
  });

  it('should render title', async () => {
    const fixture = TestBed.createComponent(App);
    await fixture.whenStable();
    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.querySelector('h1')?.textContent).toContain('World Line');
  });

  it('should render Sanring UI buttons with the sanringBtn directive applied', async () => {
    const fixture = TestBed.createComponent(App);
    await fixture.whenStable();
    const compiled = fixture.nativeElement as HTMLElement;
    const buttons = compiled.querySelectorAll('button');
    expect(buttons.length).toBeGreaterThan(0);
    // ButtonDirective 的 host binding 會把 variant/size 換算出的 class 掛上去——
    // 有掛上就代表 standalone directive import 真的生效，不是單純渲染了一個裸 <button>。
    expect(buttons[0].className).toContain('inline-flex');
  });
});
