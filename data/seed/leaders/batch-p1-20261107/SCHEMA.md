# 人物生平補齊 batch p1（2026-11-07）staged 檔格式

每個研究檔 `<group>.json`：

```json
{
  "group": "us-es",
  "researchedOn": "2026-11-07",
  "people": [
    {
      "key": "us-fdr",
      "recordIds": ["<leader_records.id>", "..."],
      "recordNameVariants": ["Franklin D. Roosevelt"],
      "wikidataQid": "Q8007",
      "name":       {"value": "Franklin D. Roosevelt", "sources": [S]},
      "nameZh":     {"value": "富蘭克林·德拉諾·羅斯福", "sources": []},
      "birthDate":  {"value": "1882-01-30", "precision": "day", "sources": [S]},
      "deathDate":  {"value": "1945-04-12", "precision": "day", "sources": [S]},
      "birthPlace": {"value": {"zh-Hant": "紐約州海德公園", "en": "Hyde Park, New York"}, "sources": [S]},
      "party":      {"value": {"zh-Hant": "民主黨", "en": "Democratic Party"}, "sources": [S]},
      "summary":    {"value": {"zh-Hant": "…", "en": "…"}, "sources": [S]},
      "portrait":   {"fileUrl": "https://commons.wikimedia.org/wiki/Special:FilePath/<File>.jpg?width=400",
                     "sourceUrl": "https://commons.wikimedia.org/wiki/File:<File>.jpg",
                     "author": "…", "commonsLicense": "PD-US / PD-USGov / CC BY-SA 4.0 …",
                     "licenseCode": "pd_expired | us_federal_pd | cc0 | cc_by | cc_by_sa",
                     "licenseUrl": "https://…", "attribution": "…", "retrievedOn": "2026-11-07"},
      "conflicts":  [{"field": "birthDate", "values": [{"value": "…", "source": S}], "note": "…"}],
      "unverified": [{"field": "party", "clue": "…", "why": "…"}]
    }
  ]
}
```

`S`（一個來源）：

```json
{"title": "頁面／條目標題", "publisher": "出版者（不可只寫自製）", "url": "https://…",
 "sourceKind": "official_record | official_history | peer_reviewed | dataset",
 "licenseCode": null, "locator": "段落／小標／頁碼", "evidence": "≤25 字的原文摘錄", "accessedOn": "2026-11-07"}
```

規則：
- 欄位不確定就整欄省略（或寫 `null`），放進 `unverified`；不可猜。
- Wikidata 只當線索（記 Q 號），**不可**當唯一來源；每個有值的欄位至少一個非 Wikidata、當天實際打開過的來源。
- 有衝突的說法放 `conflicts`，該欄不給值。
- 照片：只收 Wikimedia Commons 上授權屬 PD／CC0／CC BY／CC BY-SA 的檔案，要打開檔案頁確認授權模板、作者；拿不準就 `null`。不下載圖片。
- `nameZh` 可沿用任期紀錄裡的中文名（`sources` 留空即可，前端會顯示「待補來源」）。
