// 把新版戰役頁（demos/battle-v2.5，純靜態）複製到 public/battle/，讓它跟主程式一起出貨（網址 /battle/）。
// Angular 的 assets 只能放工作區（frontend/）裡面的路徑，所以用複製的；public/battle 是產生檔，不進版控。
// 只帶正式頁要用的：示例資料、仍是草稿的波蘭、工具與說明文件都不複製。
import { cpSync, existsSync, rmSync } from 'node:fs';
import { dirname, relative, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const src = resolve(here, '../../demos/battle-v2.5');
const dst = resolve(here, '../public/battle');
const SKIP = [/^tools(\/|$)/, /\.md$/, /^fps\.json$/, /^battles\/dunkirk-1940-example(\/|$)/, /^battles\/poland-1939(\/|$)/, /(^|\/)\.DS_Store$/];

if (!existsSync(src)) {
  console.warn('[sync-battle-page] 找不到 demos/battle-v2.5，略過');
} else {
  rmSync(dst, { recursive: true, force: true });
  cpSync(src, dst, { recursive: true, filter: (p) => !SKIP.some((re) => re.test(relative(src, p).split(sep).join('/'))) });
  console.log('[sync-battle-page] demos/battle-v2.5 → public/battle');
}
