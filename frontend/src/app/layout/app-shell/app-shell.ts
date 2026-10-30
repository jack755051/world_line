import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { ToasterComponent } from '../../components/ui/toast';

/** App shell：全版面容器＋全域 toast（PRD §8.11；Stitch W7-4：toast 在時間軸上方置中）。頂部列、圖例、時間軸都在主地圖頁內。 */
@Component({
  selector: 'wl-app-shell',
  imports: [RouterOutlet, ToasterComponent],
  host: { class: 'block h-full bg-wl-background text-wl-on-surface' },
  template: `<router-outlet /><div data-testid="toast"><sanring-toaster position="bottom-center" [stacked]="false" /></div>`,
})
export class AppShell {}
