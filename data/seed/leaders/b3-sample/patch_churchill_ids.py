"""b3-sample 補邱吉爾 bioId／任期 id（Tai 2026-11-11 10:13 第 ⑤ 項；寫庫 commit f665946）。

用法：python3 -I patch_churchill_ids.py [research.json]
- 只改 key=gb-winston-churchill 的 bioId、recordIds、paragraphs[].relatedRecordIds。
- 段落 period 與任期 [1940-05-10,1945-07-26) 重疊（半開區間）者掛新任期 id；已撤回任期 id 一律替換。
- 冪等：已套用則不寫檔。不連網、不連資料庫。
- 寫回格式同原檔：json.dumps(indent=1, ensure_ascii=False)，結尾無換行；寫前先確認原檔可逐位元組 round-trip。
"""
import json, sys, uuid

PATH = sys.argv[1] if len(sys.argv) > 1 else "research.json"
KEY = "gb-winston-churchill"
BIO_ID = "01a1c86e-c89b-70af-afe0-1ad0f4be2bf8"
RECORD_ID = "01a1c86e-c9a8-774a-92a1-bcf284ffe54d"
RETRACTED_RECORD_ID = "01a19efa-769a-7615-9705-89c66d803905"
TERM = ("1940-05-10", "1945-07-26")  # [start, end)


def dump(d):
    return json.dumps(d, ensure_ascii=False, indent=1)


def overlaps(period):
    s, e = period.get("start"), period.get("end")
    # null 起／迄視為無界；ISO 日期字串可直接比較
    return (e is None or e > TERM[0]) and (s is None or s < TERM[1])


def fix_ids(ids, want):
    out = [RECORD_ID if i == RETRACTED_RECORD_ID else i for i in ids]
    if want and RECORD_ID not in out:
        out.append(RECORD_ID)
    return list(dict.fromkeys(out))  # 去重保序


def main():
    for u in (BIO_ID, RECORD_ID):
        assert str(uuid.UUID(u)) == u, f"非法 UUID：{u}"
    raw = open(PATH, encoding="utf-8").read()
    data = json.loads(raw)
    assert dump(data) == raw, "原檔格式無法 round-trip，停止以免產生無關 diff"

    people = [p for p in data["people"] if p.get("key") == KEY]
    assert len(people) == 1, f"{KEY} 應恰有 1 筆，實得 {len(people)}"
    p = people[0]
    changes = []

    if p.get("bioId") != BIO_ID:
        assert p.get("bioId") in (None, BIO_ID), f"bioId 已有其他值：{p.get('bioId')}"
        changes.append(f"bioId: {p.get('bioId')} → {BIO_ID}")
        p["bioId"] = BIO_ID

    new = fix_ids(p.get("recordIds") or [], True)
    if new != p.get("recordIds"):
        changes.append(f"recordIds: {p.get('recordIds')} → {new}")
        p["recordIds"] = new

    for para in p.get("paragraphs", []):
        old = para.get("relatedRecordIds") or []
        new = fix_ids(old, overlaps(para.get("period") or {}))
        if new != para.get("relatedRecordIds"):
            changes.append(f"段{para.get('ord')} {para.get('period')} relatedRecordIds: {old} → {new}")
            para["relatedRecordIds"] = new

    out = dump(data)
    # 只檢 id 欄位（dbNote 說明文字本身提到撤回 id，不在本腳本範圍）
    id_fields = [p["bioId"], *p["recordIds"], *(i for x in p.get("paragraphs", []) for i in x.get("relatedRecordIds") or [])]
    assert RETRACTED_RECORD_ID not in id_fields, "邱吉爾 id 欄位仍含已撤回任期 id"
    for i in id_fields:
        assert str(uuid.UUID(i)) == i, f"非法 UUID：{i}"
    if out == raw:
        print("無變化（已套用）")
        return
    with open(PATH, "w", encoding="utf-8") as f:
        f.write(out)
    print("已寫回：")
    for c in changes:
        print(" -", c)


if __name__ == "__main__":
    main()
