import { Component } from '@angular/core';

/** 主地圖頁（`/`）。MapLibre 地圖、圖例、時間軸、來源 popover 在 C8 接上（PRD §8.2、§10 M0）。 */
@Component({
  selector: 'wl-atlas-page',
  host: { class: 'block h-full' },
  template: `<main data-testid="atlas-page" class="h-full" aria-label="主地圖"></main>`,
})
export class AtlasPage {}
