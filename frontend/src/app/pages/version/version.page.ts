import { Component, OnInit, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { LucideArrowLeft } from '@lucide/angular';
import { versionInfo } from '../../core/version';

/** 版本與變更紀錄頁（ccq 03-version-page）。 */
@Component({
  selector: 'wl-version-page',
  imports: [RouterLink, LucideArrowLeft],
  host: { class: 'block h-full' },
  template: `
    <main data-testid="version-page" class="flex min-h-full items-start justify-center bg-wl-background py-12 px-4">
      <div class="wl-paper flex w-full max-w-[640px] flex-col gap-6 px-8 py-8">
        <h1 class="wl-title1 text-center">版本資訊</h1>

        <dl class="flex flex-col gap-2 text-sm">
          <div class="flex gap-3">
            <dt class="w-24 shrink-0 font-semibold opacity-60">版本號</dt>
            <dd data-testid="version-number">{{ version }}</dd>
          </div>
          <div class="flex gap-3">
            <dt class="w-24 shrink-0 font-semibold opacity-60">建置時間</dt>
            <dd data-testid="version-build-time">{{ buildTime }}</dd>
          </div>
          <div class="flex gap-3">
            <dt class="w-24 shrink-0 font-semibold opacity-60">Commit</dt>
            <dd data-testid="version-commit" class="font-mono">{{ commit }}</dd>
          </div>
        </dl>

        <hr class="border-current opacity-10" />

        <section>
          <h2 class="wl-title1 mb-3 text-base">變更紀錄</h2>
          @if (changelog()) {
            <pre class="whitespace-pre-wrap break-words text-xs leading-relaxed opacity-80">{{ changelog() }}</pre>
          } @else if (changelogError()) {
            <p class="text-xs opacity-60">無法載入 CHANGELOG.md</p>
          } @else {
            <p class="text-xs opacity-60">載入中…</p>
          }
        </section>

        <div class="text-center">
          <a routerLink="/" data-testid="version-back"
             class="wl-btn-secondary inline-flex h-9 items-center gap-2 px-5 wl-text2">
            <svg lucideArrowLeft class="size-3.5" aria-hidden="true"></svg>回主地圖
          </a>
        </div>
      </div>
    </main>
  `,
})
export class VersionPage implements OnInit {
  protected readonly version = versionInfo.version;
  protected readonly buildTime = versionInfo.buildTime;
  protected readonly commit = versionInfo.commit;

  protected readonly changelog = signal<string | null>(null);
  protected readonly changelogError = signal(false);

  ngOnInit(): void {
    fetch('/CHANGELOG.md')
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.text();
      })
      .then((text) => this.changelog.set(text))
      .catch(() => this.changelogError.set(true));
  }
}
