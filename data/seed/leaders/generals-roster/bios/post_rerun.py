#!/usr/bin/env python3
"""來源不足補跑後處理：合併重複人物＋在 S/INSUFFICIENT_RERUN.md 追加主管要求的四項說明（可重跑；以標記取代舊段落）。

依據：World Line 主管 2026-11-12 06:32（四項說明、Nimitz 合併）；Tai 本人 2026-11-12 06:34（具名 C 級）。
由 .dev/cc-generals-insuff-post.sh 在 .dev/cc-generals-insuff-rerun.done 出現後呼叫；不 commit（由外層 shell 只 commit 自己的路徑）。
補跑前的證據（QUALITY.md 2026-11-12 04:19:33+08:00 快照、S/batch004 主 session 結果、commit 2fc70ae）固定寫在下方；補跑後狀態即時重算。
用法：python3 -I post_rerun.py [--skip-merge]
"""
import json, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(HERE))
from check_min import check  # noqa: E402

REPORT = HERE / "S" / "INSUFFICIENT_RERUN.md"
M0, M1 = "<!-- MANAGER_0632_ITEMS -->", "<!-- /MANAGER_0632_ITEMS -->"


def person(tier, nn, key):
    rj = HERE / tier / f"batch{nn}" / "research.json"
    for p in json.loads(rj.read_text(encoding="utf-8")).get("people") or []:
        if p.get("key") == key:
            return p
    return None


def fmt(r):
    if r is None:
        return "（research.json 仍無此條目）"
    return (f"{r['paragraphs']} 段／{r['zhChars']} 字；任期完整 {r['termsFull']}、只有起日 {r['termsFlagged']}、缺 {r['termsMissing']}（共 {r['terms']}）；"
            f"指揮={r['hasCommand']}、戰役={r['hasBattle']}；來源不足旗標={r['sourceInsufficient']}；達標={r['meetsMinimum']}")


def live(tier, nn, key):
    p = person(tier, nn, key)
    return fmt(check(p) if p else None)


def merge_step(skip):
    if skip:
        return {"status": "skipped(--skip-merge)"}
    rel = "data/seed/leaders/generals-roster/bios/S/batch012/research.json"
    dirty = subprocess.run(["git", "-C", str(REPO), "diff", "--quiet", "--", rel]).returncode != 0
    if dirty:
        return {"status": "skipped_uncommitted_changes", "note": "S/batch012/research.json 有未 commit 的補跑變更（補跑可能中途停止），為免把未驗證內容一起 commit，本次不合併"}
    r = subprocess.run([sys.executable, "-I", str(HERE / "patch_merge_duplicates.py")], capture_output=True, text=True)
    try:
        return json.loads(r.stdout.strip().splitlines()[-1])[0]
    except Exception:
        return {"status": "error", "out": (r.stdout + r.stderr)[-600:]}


def build(merge):
    L = [M0, "", "## 主管 2026-11-12 06:32 要求的四項說明", ""]
    L += ["### (a) S 級少的那 1 人：海因茨·古德里安（Heinz Guderian，key=heinzguderian，S/batch004）", "",
          "- `selection.json` 的 S 共 103 人，S/batch004 排 5 人（沃尔弗拉姆·冯·里希特霍芬、海因茨·古德里安、瓦尔特·冯·布劳希奇、瓦尔特·莫德尔、羅伯特·馮·格萊姆）；但 `S/batch004/research.json` 的 `people` 只有 4 筆，缺 heinzguderian，所以 QUALITY.md 讀到 102 人。",
          "- 該批主 session（`.dev/cc-generals-bios-S-b004-sonnet.json`，USD 1.4506，2026-11-12 00:01–00:08 Asia/Taipei）結尾自稱「5 人都寫成 research.json」，表中列古德里安 5 段、約 600 字，並註明「古德里安的字數取自程式的估算……他的那一行我沒有逐字核對」；實際檔案只留下他的 3 筆來源（`lemo-guderian`、`db-guderian`、`gnd-guderian`），人物條目沒有寫進去。",
          "- 主迴圈的 `check_min.py`／`verify.py` 只檢查檔內已有的人，不比對名單，所以沒抓到；commit 2fc70ae 的訊息仍列了古德里安。",
          "- 處理：`collect_insuff.py` 改為比對 `selection.json`，把漏條目者列入補跑（reason=missing_entry），補跑提示要求為他新增完整條目並可沿用既有來源。",
          f"- 補跑後狀態：{live('S', '004', 'heinzguderian')}", ""]
    L += ["### (b) 未達標 59 人 vs 來源不足 64 人", "",
          "- 兩個數字量的是不同的東西：「未達標」＝`check_min.check()` 的 meetsMinimum=False；「來源不足」＝該人任何一筆 gap 的 note 以「來源不足」或「篇幅不足：」開頭（或 sourceInsufficient=true）。",
          "- 59 個未達標者全部也帶來源不足旗標，所以 64 − 59 ＝ 5 人是「已達最低標準、但某一項 gap 寫了『來源不足：…』」，旗標是針對單一細項，不是整份不足：",
          "  1. 威廉·凱特爾（wilhelmkeitel，S/batch002）：4 段／497 字、任期 3/3；gap `paragraph:battle`「來源不足：…未載本人指揮的具體戰役」。",
          "  2. 阿爾弗雷德·約德爾（alfredjodl，S/batch005）：3 段／378 字、任期 3/3；gap `paragraph:battle`「來源不足：…未寫其親自指揮的具名戰役」。",
          "  3. 喬治·巴頓（georgespatton，S/batch011）：4 段／507 字、任期 7/7；gap `field:battles`「來源不足：LoC 指引只有年表式職務……history.army.mil 403」。",
          "  4. 永野修身（osaminagano，S/batch015）：4 段／408 字、任期 3/3；gap `paragraph:major-battles`「來源不足：…軍令部總長期間之具體作戰敘述」。",
          "  5. 弗朗茨·康拉德·馮·赫岑多夫（franzconradvonhotzendorf，S/batch019）：4 段／534 字、任期 4/4；gap `paragraph:source`「來源不足：1914-1918-online 遇 Anubis 挑戰頁……」。",
          "- 另外兩個數字都把 Nimitz 算了兩次（chesterwnimitz、chesternimitz 同在 S/batch012），以人計是未達標 58 人、來源不足 63 人；古德里安因無條目，兩個數字都沒算到他。",
          "- 本次補跑名單（新規則）包含這 5 人，讓他們有機會補上細項並清掉旗標。", ""]
    m = merge or {}
    L += ["### (c) chesterwnimitz 與 chesternimitz 合併", "",
          "- 兩筆在 S/batch012，補跑前內容逐字相同（3 段／351 字、任期 2 完整＋1 只有起日、citation 各 23 筆、gap 6 筆，含同一筆 `field:identity`「名單重複」gap）。roster.json 從兩個索引頁各收了一次（『Chester Nimitz』與『Chester W. Nimitz』）。",
          "- 補跑名單只列 chesterwnimitz（`collect_insuff.py` 的 DUPLICATES），避免重複花費。",
          "- 合併由 `patch_merge_duplicates.py` 在補跑結束後執行：兩筆擇優保留（meetsMinimum → 完整任期數 → citation 數 → 字數；全同保留 chesterwnimitz），被丟棄者的 citation 按同段落／同職位以 sourceKey＋quote 去重併入，gaps、searchLog 去重併入，頂層 sources 共用不刪；合併經過記在保留者的 `field:identity` gap（不新增欄位）；合併後跑 verify.py，不過就還原。",
          f"- 本次執行結果：狀態＝{m.get('status')}；保留＝{m.get('kept', '—')}、刪除＝{m.get('dropped', '—')}；併入 citation {m.get('added_citations', '—')} 筆、gap {m.get('added_gaps', '—')} 筆、searchLog {m.get('added_searchLog', '—')} 筆。" + (f" 備註：{m.get('note') or m.get('verify_tail') or m.get('out')}" if m.get('status') not in ('merged',) else ""),
          f"- 合併後（保留者）狀態：{live('S', '012', 'chesterwnimitz') if person('S', '012', 'chesterwnimitz') else live('S', '012', 'chesternimitz')}",
          "- roster.json／selection.json 仍各有兩筆（建構產物，未手改）；日後重建名單時應在 build_roster.py 去重。", ""]
    L += ["### (d) 隆美爾（4 段／509 字）為何未達標", "",
          "- 主管猜得對：沒過的是「每個職位都要有起迄日」。篇幅（4 段 ≥3、509 字 ≥300）、指揮職、主要戰役都過了。",
          "- QUALITY.md 時點（S/batch001 `min-check.round2.json`）：5 個職位中 4 個有起迄日，1 個只有起日——非洲裝甲集群（`rommel-panzergruppe-afrika`，起 1941-07-01，迄日空白），已寫 gap「待查證：缺迄日」；`check_min.py` 規定 termsFlagged 必須為 0，所以判未達標（並帶來源不足旗標，因 `paragraph:length` gap 以「來源不足：」開頭）。",
          "- 另有第七裝甲師師長因缺起日沒寫進 positions（gap「待查證：缺起日」），這筆不計入任期檢查，但正文提到；第一輪時是任期 1 完整＋3 只有起日，重跑後補到 4＋1。",
          f"- 補跑後狀態：{live('S', '001', 'erwinrommel')}", ""]
    L += [M1, ""]
    return "\n".join(L)


def main():
    merge = merge_step("--skip-merge" in sys.argv)
    block = build(merge)
    txt = REPORT.read_text(encoding="utf-8") if REPORT.exists() else "# 將領來源不足補跑報告\n\n（補跑腳本未產出主報告）\n"
    if M0 in txt and M1 in txt:
        pre, rest = txt.split(M0, 1)
        _, post = rest.split(M1, 1)
        txt = pre.rstrip("\n") + "\n\n" + block + post.lstrip("\n")
    else:
        txt = txt.rstrip("\n") + "\n\n" + block
    txt = txt.replace("# 將領 S 級來源不足補跑報告", "# 將領來源不足補跑報告（S 全部＋A 級規則變更前批次；新規則：具名 C 級）", 1)
    REPORT.write_text(txt, encoding="utf-8")
    print(json.dumps({"report": str(REPORT.relative_to(REPO)), "merge": merge}, ensure_ascii=False))


if __name__ == "__main__":
    main()
