import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';

/**
 * App shell：全版面容器。
 * Top bar、右側面板、時間軸、圖例（DESIGN.md Layout & Spacing）等 A9 Stitch 稿定稿、C8 時再加入，骨架只放 router-outlet。
 */
@Component({
  selector: 'wl-app-shell',
  imports: [RouterOutlet],
  host: { class: 'block h-full bg-wl-background text-wl-on-surface' },
  template: '<router-outlet />',
})
export class AppShell {}
