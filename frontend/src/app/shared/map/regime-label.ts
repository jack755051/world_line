import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';

/** 多邊形投影到畫面上的外框（像素）。標籤位置仍由 Mercator `project` 決定，這裡只用來看形狀。 */
export interface RegimeLabelScreen {
  w: number;
  h: number;
}

export interface RegimeLabelChrome {
  transform: string;
  background: string;
  padding: string;
  borderRadius: string;
  boxShadow: string;
}

/**
 * 半透明紙色底板（`--wl-color-surface` #faf7f0）。
 * 比原本的紙色 text-shadow 暈邊穩：淺色、深色、接近紙色的填色上都讀得清楚，又還透得出底下的政權色。
 */
export const REGIME_LABEL_PLATE = {
  background: 'rgb(250 247 240 / 0.82)',
  padding: '2px 6px',
  borderRadius: '2px',
  boxShadow: '0 0 0 1px rgb(58 47 40 / 0.16)',
} as const;

/**
 * 國名／政權名稱的畫面樣式。
 * `screen` 是該政權多邊形在 Mercator 投影後的外框。外框再扁、再高（細長政權）也不順著長軸轉，文字永遠水平。
 */
export function regimeLabelStyle(screen?: RegimeLabelScreen): RegimeLabelChrome {
  // 長寬只說明形狀；方向固定 0°，不把 atan2(screen.h, screen.w) 寫進 transform。
  void screen;
  return {
    transform: 'translate(-50%, -50%) rotate(0deg)',
    background: REGIME_LABEL_PLATE.background,
    padding: REGIME_LABEL_PLATE.padding,
    borderRadius: REGIME_LABEL_PLATE.borderRadius,
    boxShadow: REGIME_LABEL_PLATE.boxShadow,
  };
}

/**
 * 地圖上的一顆政權／國名標籤。HTML 疊在 MapLibre 畫布上（不是 symbol layer），
 * 所以方向不受地圖 bearing 影響，底板用一般 CSS 即可。
 */
@Component({
  selector: 'wl-regime-map-label',
  changeDetection: ChangeDetectionStrategy.OnPush,
  // 宿主不佔版面，內層 span 的 absolute 仍相對地圖上的標籤層定位（與原本直接放 span 相同）。
  host: { style: 'display: contents' },
  template: `
    <span
      data-testid="map-regime-label"
      data-orientation="horizontal"
      [attr.data-regime-id]="regimeId()"
      class="wl-regime-label absolute whitespace-nowrap"
      [style.left.px]="x()"
      [style.top.px]="y()"
      [style.transform]="chrome().transform"
      [style.background]="chrome().background"
      [style.padding]="chrome().padding"
      [style.border-radius]="chrome().borderRadius"
      [style.box-shadow]="chrome().boxShadow"
      >{{ text() }}</span
    >
  `,
})
export class RegimeMapLabel {
  readonly regimeId = input.required<string>();
  readonly text = input.required<string>();
  readonly x = input.required<number>();
  readonly y = input.required<number>();
  /** 投影後外框。不改變座標，也不改變角度。 */
  readonly screenW = input(0);
  readonly screenH = input(0);
  protected readonly chrome = computed(() =>
    regimeLabelStyle({ w: this.screenW(), h: this.screenH() }),
  );
}
