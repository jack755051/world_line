#!/usr/bin/env python3
"""連結候選（gap-830 L01）：未連結任期與現有生平同名，且同政權或繼承政權、任期相鄰或重疊 → 確認為同一人後 PATCH person。
不改生平內容；只接「目前 person_id 為空」的任期。預設試跑；--send 寫入。"""
import argparse, json, os, re, sys, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from send_batch import api_key, call, sql
LINKS = [  # (record id, bio id, 判斷依據)
 ("01a1aa4a-b7d4-788b-8b75-fd88095b5a21", "01a19f15-3219-7d80-bda3-689198e9ac72", "愛爾蘭自由邦國王 1922-12-06 起；與英國君主喬治五世同一人（生平已有英國任期 1910–1936）"),
 ("01a1aa4a-b7d4-7a65-82d3-010a08ce3428", "01a19f15-32c5-708d-b01b-9e4020a30a0a", "愛爾蘭自由邦國王 1936；與英國君主愛德華八世同一人"),
 ("01a1aa4a-b7d4-7c46-9ced-c44b716a28e6", "01a1aa4a-da2e-7907-b1fa-858d55b7918a", "愛爾蘭自由邦國王（僅對外關係）1936–1937；與英國君主喬治六世同一人"),
 ("01a1aa4a-4a50-77ba-b268-b2c6d6aaa2d8", "01a1b48b-c890-7320-84f4-1442207f5f03", "西班牙共和國紀錄 1939-03 至 04-01，緊接西班牙國同名任期（1939-04-01 起）"),
 ("01a1aa4a-4a4f-793a-9272-bca7804219c8", "01a1b48b-c890-7320-84f4-1442207f5f03", "同上"),
 ("96cc0e9f-dfbe-4d54-a546-83cdc399becf", "eb6e6997-c44d-40fe-85a7-2ba4d0b324dd", "祕魯 1930-08-28 起兼部長會議主席；與同日起任國家元首的同名者同一人"),
 ("3990200a-4f96-4b40-a092-d6f965e48b72", "65946b65-9aa4-4dea-8ea1-116090e84eea", "委內瑞拉 1914–1922 代行元首；生平已有同期政府首腦任期"),
 ("4d745611-6b2d-4394-9eda-13472f507956", "01a1b488-1462-7bec-aa9e-7bccbbd15bc2", "委內瑞拉 1914–1922 當選總統兼陸軍總司令；與前後連續任期同一人"),
 ("76096e38-ab4f-4959-a1fd-81fae368ca0e", "01a1b488-1424-760c-bdd1-9a20523a5a85", "海地 1915-01-19 對立政府，緊接其 1915-02-22 起任期"),
 ("2f3df903-8527-4114-b073-54905200fa98", "01a1b488-1424-760c-bdd1-9a20523a5a85", "同上"),
]
ap = argparse.ArgumentParser(); ap.add_argument("--base", default="http://127.0.0.1:5052/api/v1"); ap.add_argument("--db", default="worldline_borders_dev"); ap.add_argument("--send", action="store_true")
a = ap.parse_args()
if ":5051" in a.base: sys.exit("拒絕 5051")
ids = ",".join(f"'{r}'" for r, _, _ in LINKS)
cur = {r[0]: r[1] for r in sql(a.db, f"select id, coalesce(person_id::text,'') from leader_records where retracted_at is null and id in ({ids})")}
live = {r[0] for r in sql(a.db, "select id from leader_bios where retracted_at is null")}
plan = [(r, b, why) for r, b, why in LINKS if r in cur and not cur[r] and b in live]
for r, b, why in LINKS:
    print(("✓ " if (r, b, why) in plan else "✗ 略過 ") + f"{r} → {b}：{why}")
print(f"計畫：連結 {len(plan)}")
if not a.send: sys.exit("（試跑：未寫入）")
key = api_key()
for r, b, _ in plan:
    st, res = call(a.base, "PATCH", f"/leader-records/{r}/person", {"personId": b}, key)
    print(r, st if st != 200 else "ok")
