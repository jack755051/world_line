import { Component, computed, input } from '@angular/core';
import { formatEdtfDateLabel, formatEdtfQualifierLabel, parseEdtf } from '../core/time/edtf-display';

/**
 * 顯示一個 EDTF 日期字串（任務 3.10，PRD Story 5「模糊/爭議年份的呈現」）——`historical_
 * events.start_edtf`/`end_edtf` 這種原始字串（例如 `"0220"`、`"1046?"`）該怎麼呈現給
 * 使用者看，集中在這一個元件，不要讓每個要顯示事件日期的地方各自寫一次格式化邏輯。
 *
 * **AC#1（精度層級）**：只顯示史料實際記載到的精度——年精度就只顯示到年，不會因為
 * 後端計算 `start_decimal` 內部把月/日補成 1 月 1 日，就跟著在畫面上偽造出「1月1日」
 * 這種比史料本身更精確的假象。做法：`formatEdtfDateLabel()` 只在解析結果真的有
 * 月/日欄位時才加進顯示字串，精度層級本身就靠「顯示到哪一級」直接表達，不另外疊加一段
 * 「（年精度）」這種文字說明——省略掉的部分自然就是「不知道」，不需要額外標注。
 *
 * **AC#2（不確定性提示）**：`?`/`~` 尾綴標記對應到「推測年份」/「約略年份」，用
 * `<span class="edtf-date-qualifier">` 包起來，樣式上跟主要日期文字分開（次要、較淡的
 * 顏色），不會讓使用者誤把「推測」當成跟其他確定日期一樣的事實陳述。
 *
 * 解析失敗（理論上不該發生，資料庫裡的字串都是後端 `EdtfService` 驗證過才寫進去的，
 * 見 `edtf-display.ts` 的說明）時直接顯示原始字串，不整個消失或報錯——顯示「看不懂的
 * 原始字串」好過「什麼都不顯示」。
 */
@Component({
  selector: 'app-edtf-date',
  standalone: true,
  templateUrl: './edtf-date.html',
  styleUrl: './edtf-date.scss',
})
export class EdtfDateComponent {
  readonly value = input.required<string>();

  protected readonly parsed = computed(() => parseEdtf(this.value()));

  protected readonly dateLabel = computed(() => {
    const parsed = this.parsed();
    return parsed ? formatEdtfDateLabel(parsed) : this.value();
  });

  protected readonly qualifierLabel = computed(() => {
    const parsed = this.parsed();
    return parsed ? formatEdtfQualifierLabel(parsed.qualifier) : null;
  });
}
