"""B3 試跑 50 人：挑選名單產生器（只讀 5442，不寫庫）。

用法：python3 -I build_selection.py   → 寫出同目錄 selection.json
連線：docker exec worldline-borders-dev-db psql，PGOPTIONS=-c default_transaction_read_only=on（同 gap-830 send_batch.py），只 SELECT。
挑選依據：Tai 2026-11-11 09:30（試跑 50 人；資料厚薄、各洲、元首／首腦、君主／總統／總理／軍人等類型；避開 b3-sample 5 人）。
厚薄（thickness）是預估「公開 A／B 來源可得的生平深度」，不是 DB 欄位：
  厚＝國家級傳記辭典／官方傳記頁多且詳；中＝有官方或辭典條目但較短；薄＝只有名簿、權威檔或零星條目。
"""
import json, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CONTAINER, DB = "worldline-borders-dev-db", "worldline_borders_dev"
EXCLUDE = {  # b3-sample 已做的 5 人（bio id 或名稱）
    "01a19f15-35f4-7d9a-847a-aeccc98305ec",  # Hitler
    "62241525-b2f1-4931-bfb3-30ecf9dd3094",  # 東條英機
    "1b13259b-f739-4d2e-b0a7-693a20e1412f",  # Vargas
    "01a1c446-a421-72a6-8d95-7c0372400146",  # Jadambaa
}  # 邱吉爾在 5442 無有效 bio，自然不會被選到

# (bio_id, continent, subregion, primaryType, typeTags, thickness, reason)
PICKS = [
    # ---- 批 01 ----
    ("0ff6f55e-8f9c-49aa-b9ba-5858a17c9dc3", "歐洲", "南歐", "總理", ["獨裁者", "法西斯黨魁"], "厚", "義大利首相、法西斯政權實際掌權者；首腦型獨裁者，與希特勒對照"),
    ("01a1b4af-e4ae-7ffe-b91b-13f90ca7ea6b", "亞洲", "南亞", "君主", ["拉納家族攝政下的虛位君主"], "薄", "尼泊爾國王；英文權威來源少，測試薄資料南亞君主"),
    ("01a1b54f-2c8f-71a2-a16c-fb34276fb32c", "大洋洲", "澳洲", "總理", ["議會制", "自治領"], "中", "澳洲聯邦總理；大洋洲唯一在 5442 的領導人"),
    ("01a1b4b0-6fa7-77d3-b478-e72f161b3319", "非洲", "北非", "君主", ["蘇丹改稱國王"], "中", "埃及蘇丹／國王；非洲君主"),
    ("01a1b488-1424-760c-bdd1-9a20523a5a85", "美洲", "加勒比海", "總統", ["短期", "遇刺"], "薄", "海地總統（1915，數月後遇害）；加勒比海資料薄的短期元首"),
    # ---- 批 02 ----
    ("01a1b492-3efd-7d05-8a70-3f38fdf9d599", "歐洲", "東歐", "總理", ["實際掌權者", "共產黨總書記"], "厚", "蘇聯人民委員會主席（1941–），長期以黨職實際掌權；de_facto_leader 型"),
    ("e8e4a14e-09b9-40a2-99b5-153deca6b12b", "亞洲", "東亞", "總理", ["華族", "三度組閣"], "厚", "日本首相（三次組閣），首相官邸／NDL 來源豐富"),
    ("01a1c406-24d5-7dc1-9bb0-21533fb0fd28", "亞洲", "東亞", "總理", ["軍人", "北洋", "短期"], "薄", "北洋政府國務總理（1926 約一個半月）；中國資料薄的人物"),
    ("01a1b4b5-fa07-7891-b5f8-6b36cbc96506", "亞洲", "西亞", "君主", ["伊瑪目", "宗教領袖"], "薄", "葉門伊瑪目／國王；阿拉伯半島資料薄的神權君主"),
    ("01a1aa4a-da74-748f-aea8-7d3802bce69c", "美洲", "北美", "總統", ["軍人出身", "改革派"], "厚", "墨西哥總統（1934–40），官方與學術來源多"),
    # ---- 批 03 ----
    ("2e92f31f-cda7-4be2-bdb3-953fac108b0d", "歐洲", "南歐", "君主", ["立憲君主", "兼阿爾巴尼亞國王"], "厚", "義大利國王；跨政權（兼阿爾巴尼亞）元首"),
    ("01a1b520-ef3c-70f4-887f-70bf97bd141e", "亞洲", "東亞", "君主", ["末代皇帝", "被併吞"], "中", "大韓帝國純宗；政權被併吞的末代君主"),
    ("01a1c42c-5fe2-7e73-bd0c-9fe30979161a", "非洲", "北非", "總理", ["短期", "多次組閣"], "薄", "埃及首相（5442 記為 head_of_state：1936-04-28–05-08 國王出缺期間由內閣行使王權；待研究確認）；5442 已記出生年三說（來源矛盾），測試薄資料＋矛盾"),
    ("01a1c411-2492-7689-8723-43b64bb523c0", "歐洲", "南歐", "總理", ["第一共和", "短期"], "薄", "葡萄牙第一共和總理（1923，約一個月）；歐洲資料薄的短期首腦"),
    ("01a1b48b-c87a-768a-b372-2918df397b6c", "美洲", "北美", "總統", ["四任", "戰時"], "厚", "美國總統；官方圖書館與國會來源極多"),
    # ---- 批 04 ----
    ("01a1b4b5-f9bc-7f2f-90ba-f2af428ba89c", "歐洲", "東歐", "君主", ["專制君主", "末代沙皇", "遇害"], "厚", "俄國末代沙皇；專制君主"),
    ("01a1b4b2-2f65-7cca-9a4b-ff875f18c192", "亞洲", "東亞", "君主", ["天皇", "戰後在位"], "厚", "日本天皇（1926–1989）；生平大幅超出範圍，測試範圍外段落寫法"),
    ("01a1b512-8b32-794e-b679-4862ab380cc8", "亞洲", "內亞", "元首", ["共產政權", "後任總理", "被處決"], "薄", "蒙古人民共和國主席團主席（後任總理，1937 遭處決）；內亞資料薄"),
    ("01a1c30e-dcb2-7378-a341-4f30f8de6ae5", "亞洲", "高加索", "總理", ["短命共和國"], "薄", "亞美尼亞第一共和國總理；高加索資料薄"),
    ("477e851d-8e39-4da5-8a50-33d0c8a77067", "美洲", "南美", "總統", ["兩度任期", "遭政變推翻"], "中", "阿根廷總統（1916–22、1928–30）"),
    # ---- 批 05 ----
    ("ef990cdf-5286-44c4-8e0a-1e8aaa1c629b", "歐洲", "西歐", "總理", ["議會制", "戰時"], "厚", "法國總理（兩任）；法國第三共和代表"),
    ("01a1b490-dcc7-76dc-82d7-da76fb59d7d2", "亞洲", "東亞", "元首", ["軍人", "兼首腦", "黨領袖"], "厚", "國民政府主席兼行政院長、軍事委員會委員長；元首／首腦／軍人兼具"),
    ("01a1b4b2-2f5f-789f-a0f3-025285dd9ac1", "亞洲", "南亞", "君主", ["世襲王朝第二代"], "薄", "不丹國王；喜馬拉雅資料薄"),
    ("01a1b4b5-fa0c-7978-b7ac-e9ed00d0aa5c", "亞洲", "西亞", "君主", ["建國者", "征服"], "中", "沙烏地阿拉伯建國國王"),
    ("01a1b54f-2ce7-7c99-b2b3-acac8a77d7ec", "美洲", "南美", "總統", ["臨時", "短期"], "薄", "巴拉圭臨時總統（1924）；南美資料薄"),
    # ---- 批 06 ----
    ("01a1b48b-c890-7320-84f4-1442207f5f03", "歐洲", "南歐", "元首", ["軍人", "內戰勝方", "獨裁者"], "厚", "西班牙國家元首（1939–75）；軍人元首，生平大幅超出範圍"),
    ("01a1b51c-82f5-769f-b906-e1ae5f2acad8", "亞洲", "東亞", "總理", ["軍人", "北洋軍閥", "多次組閣"], "中", "北洋政府國務總理（多次）、後任臨時執政；軍閥型首腦"),
    ("01a1b512-8b5a-7201-b097-0b0137dd4d94", "亞洲", "南亞", "殖民地總督", ["印度總督", "貴族"], "中", "英屬印度總督（5442 記為 head_of_government）；殖民總督型"),
    ("01a1b52c-f9a5-74dc-a80f-e32ef42202f1", "亞洲", "西亞", "總理", ["大維齊爾", "統一與進步委員會", "遇刺"], "中", "鄂圖曼帝國大維齊爾；一戰期間實權人物"),
    ("5f291e78-8724-4192-a409-482f92ccf1de", "美洲", "南美", "總統", ["軍人", "政變"], "中", "阿根廷 1930 政變後臨時總統；軍人政變型"),
    # ---- 批 07 ----
    ("01a1b4b5-7275-7a4c-a36c-723359599508", "歐洲", "中歐", "元首", ["軍人", "國家元首後任總理", "實際掌權者"], "中", "波蘭臨時國家元首、兩度總理，1926 後實際掌權；軍人型"),
    ("01a1b539-97a9-708b-a146-32fcdedf11ad", "亞洲", "內亞", "元首", ["軍人", "實際掌權者", "共產政權"], "中", "蒙古主席團主席（1929–30），後任總理與元帥實際掌權"),
    ("01a1b52a-61bc-702e-ba89-f161463fd740", "亞洲", "東南亞", "殖民地總督", ["軍人", "亞齊戰爭"], "中", "荷屬東印度總督（5442 記為 head_of_government）；東南亞殖民總督"),
    ("01a1b492-3f04-7906-a59b-b9bfcc8f374d", "亞洲", "西亞", "總統", ["軍人", "建國者"], "厚", "土耳其共和國首任總統；軍人建國者"),
    ("01a1b488-13d8-7337-a49a-f44a35ca1e6d", "美洲", "加勒比海", "總統", ["威權", "遭推翻"], "中", "古巴總統（1925–33）"),
    # ---- 批 08 ----
    ("01a1b4af-e4eb-720d-9ddd-df710ac38339", "歐洲", "中歐", "攝政", ["軍人（海軍上將）", "無國王的王國"], "中", "匈牙利攝政（1920–44）；攝政型元首"),
    ("01a1b4b0-700e-7f42-85f7-aa94c6275d85", "亞洲", "中亞", "君主", ["幼年即位", "戰後在位"], "中", "阿富汗國王（1933–73）"),
    ("01a1b4b2-2faf-7405-999a-8394816e968b", "亞洲", "西亞", "君主", ["軍人", "政變建立王朝", "遜位"], "中", "伊朗國王；軍人出身、先任首相後建立新王朝"),
    ("01a1aa4a-da3c-785a-9054-1780b3382cc8", "美洲", "北美", "總統", ["軍人", "長期執政", "流亡"], "厚", "墨西哥總統（至 1911）；生平大半在範圍前"),
    ("01a1b4b2-2f8a-7c19-bc59-9daf906fcd97", "美洲", "中美", "總統", ["軍人（國民警衛隊）", "家族統治"], "中", "尼加拉瓜總統；軍人型"),
    # ---- 批 09 ----
    ("01a1b4b0-6fce-7392-8b0a-241baf36d38f", "歐洲", "南歐", "總理", ["文人獨裁", "新國家體制"], "厚", "葡萄牙總理（1932–68）；文人獨裁首腦"),
    ("01a1b4c1-cdc3-7a47-9627-d2a41b653e5c", "歐洲", "中歐", "元首", ["自由市", "參議院議長兼元首"], "薄", "但澤自由市參議院議長；特殊政體、資料薄"),
    ("01a1c34f-3f09-7d5b-88a3-c14735348d79", "歐洲", "中歐", "總理", ["傀儡政權", "末任"], "薄", "斯洛伐克國末任總理（1944–45）；資料薄"),
    ("01a1b488-147a-7166-9528-0f859bb609dd", "美洲", "加勒比海", "總統", ["軍人", "獨裁者", "遇刺"], "中", "多明尼加總統、長期實際掌權"),
    ("01a1b4af-e4cc-783b-b657-f81348ad4493", "美洲", "中美", "總統", ["軍人", "獨裁者"], "中", "瓜地馬拉總統（1931–44）"),
    # ---- 批 10 ----
    ("01a1b4b2-2f94-7854-ace0-656502c9db1d", "歐洲", "中歐", "總統", ["建國者", "學者"], "厚", "捷克斯洛伐克首任總統"),
    ("PIUS-XI", "歐洲", "南歐", "君主", ["教宗", "宗教領袖", "選任君主"], "中", "梵蒂岡城國元首（教宗）；選任制宗教君主"),
    ("01a1b4c0-2f7a-7550-9122-c9dbf6f853f9", "歐洲", "西歐", "元首", ["聯邦委員會輪值主席", "合議制"], "中", "瑞士聯邦主席（多次輪值）；合議制元首"),
    ("FAISAL-I", "亞洲", "西亞", "君主", ["委任統治後獨立", "兼敘利亞國王"], "中", "伊拉克國王（5442 只收 1932 獨立後）"),
    ("453b3d70-de7b-40e9-abd6-642afa07ae47", "美洲", "南美", "總統", ["兩度任期", "長期執政", "遭政變推翻"], "中", "秘魯總統（1908–12、1919–30）"),
]
EXACT = {"PIUS-XI": "Pius XI", "FAISAL-I": "Faisal I"}


def q_json(sql):
    cmd = ["docker", "exec", "-i", "-e", "PGOPTIONS=-c default_transaction_read_only=on", CONTAINER,
           "psql", "-U", "worldline", "-d", DB, "-At", "-v", "ON_ERROR_STOP=1", "-c", sql]
    out = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout.strip()
    return json.loads(out or "[]")


def main():
    assert q_json("select json_agg(current_setting('default_transaction_read_only'))")[0] == "on"
    rows = q_json("""
select coalesce(json_agg(t),'[]') from (
 select b.id, b.name, b.name_zh, b.birth_date::text birth, b.death_date::text death,
  (select count(*) from leader_bio_field_citations c where c.bio_id=b.id and c.retracted_at is null) "fieldCitations",
  (select count(*) from leader_bio_gaps g where g.bio_id=b.id and g.retracted_at is null and g.resolved_at is null) "openGaps",
  (select json_agg(json_build_object('recordId',r.id,'role',r.role,'title',r.title,'validPeriod',r.valid_period::text,
     'verified',r.verified,'regimeId',rg.id,'regimeSlug',rg.slug,
     'regimeZh',(select n.display->>'zh-Hant' from regime_names n where n.regime_id=rg.id and n.is_primary and n.retracted_at is null limit 1),
     'regimeEn',(select n.display->>'en' from regime_names n where n.regime_id=rg.id and n.is_primary and n.retracted_at is null limit 1))
     order by lower(r.valid_period), r.role)
   from leader_records r join regimes rg on rg.id=r.regime_id where r.person_id=b.id and r.retracted_at is null) records
 from leader_bios b where b.retracted_at is null and not b.is_test and b.superseded_by is null) t""")
    by_id = {r["id"]: r for r in rows}
    by_name = {}
    for r in rows:
        by_name.setdefault(r["name"], []).append(r)
    people, seen = [], set()
    for i, (bid, cont, sub, ptype, tags, thick, reason) in enumerate(PICKS):
        if bid in EXACT:
            m = by_name.get(EXACT[bid], [])
            assert len(m) == 1, (bid, m)
            r = m[0]
        else:
            r = by_id[bid]
        assert r["id"] not in EXCLUDE and r["id"] not in seen, r["name"]
        seen.add(r["id"])
        recs = r["records"] or []
        roles = sorted({x["role"] for x in recs})
        people.append({
            "batch": f"{i // 5 + 1:02d}", "bioId": r["id"], "name": r["name"], "nameZh": r["name_zh"],
            "birth": r["birth"], "death": r["death"], "continent": cont, "subregion": sub,
            "primaryType": ptype, "typeTags": tags,
            "roles": roles, "thickness": thick, "reason": reason,
            "fieldCitations": r["fieldCitations"], "openGaps": r["openGaps"],
            "recordIds": [x["recordId"] for x in recs], "records": recs,
        })
    assert len(people) == 50
    out = {
        "trial": "b3-trial", "selectedOn": "2026-11-11",
        "decision": "Tai 2026-11-11 09:30（試跑 50 人、Sonnet 研究＋Opus 審查、上限 60 USD、不寫庫不 push）＋09:35（Q1–Q10 定案）",
        "excluded": ["希特勒", "邱吉爾", "東條英機", "瓦加斯", "扎丹巴（b3-sample 已做）"],
        "db": "5442 worldline_borders_dev（default_transaction_read_only=on，只 SELECT）",
        "thicknessNote": "厚／中／薄為預估公開 A／B 來源深度，非 DB 欄位；fieldCitations／openGaps 是 5442 現況，僅供參考",
        "batchSize": 5, "people": people,
    }
    (HERE / "selection.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    from collections import Counter
    for k in ("continent", "thickness", "primaryType"):
        print(k, dict(Counter(p[k] for p in people)))
    print("roles", dict(Counter("+".join(p["roles"]) for p in people)))


if __name__ == "__main__":
    sys.exit(main())
