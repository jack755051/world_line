import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';

/** 找不到頁面（PRD §8.11）。文案與版面待 A9 Stitch 稿定稿後調整。 */
@Component({
  selector: 'wl-not-found-page',
  imports: [RouterLink],
  host: { class: 'block h-full' },
  template: `
    <main data-testid="not-found-page" class="flex h-full flex-col items-center justify-center gap-3">
      <h1 class="font-wl-serif text-[length:var(--wl-type-title1-size)] font-semibold">找不到頁面</h1>
      <a routerLink="/" class="text-wl-secondary underline">回到主地圖</a>
    </main>
  `,
})
export class NotFoundPage {}
