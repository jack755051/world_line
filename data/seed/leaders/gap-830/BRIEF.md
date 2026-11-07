# 研究員工作說明（gap-830，每批相同）

> 派工與用量規則見 `WORKFLOW.md`（只讀本資料夾與當批檔案；輸出限長；不重讀整個 repo）。

You research sourced biographical facts for heads of state and government in a historical-map project. Your output is one staged JSON file. Do NOT write to any database or API, do not run docker, psql or any HTTP POST, and do not edit any other file.

1. Read `<batch>/worklist.json`. It lists name groups from our tenure records, with record ids, regimes and the first term start date.
2. Follow `SCHEMA.md` in this folder and the person/source format in `../batch-p1-20261107/SCHEMA.md` exactly.
3. Write `<batch>/research.json`.

## Identity first
- Merge aliases of the same person into one entry with several `groupKeys`. For example, one king may appear under two regimes with differently spelled names.
- Split different people who share a name into separate entries, each with only their own record ids. Check the regime and dates.
- If identity is uncertain, or the group is a collective body, put it in `staging` with the reason.
- `recordNameVariants` must contain the exact `name` strings of the groups you assign to that person.

## Already has a biography?
`existing_bios.tsv` lists everyone who already has a biography, as tab-separated id, name, zh name, birth year and death year.
- If a worklist group is one of these people (the same person, e.g. the same leader under another regime's record or another spelling), do NOT research them again.
- Write a people entry with only `key`, `groupKeys`, `recordIds`, `recordNameVariants`, `existingBioId` (the id from the file) and `linkEvidence` (one sentence: name, regime and dates showing it is the same person).
- If you are unsure, use staging.

## Fields
name, nameZh (common zh-Hant rendering; no source needed), birthDate+precision, deathDate+precision, birthPlace {zh-Hant, en}, party {zh-Hant, en}, summary {zh-Hant, en}, wikidataQid, portrait.

- Omit party for monarchs, popes and other non-partisan offices.
- Give a party value only if the source ties it to the period of the person's terms in the worklist. If the source attaches it to a different period, or the person changed party, omit it and add an `unverified` entry.
- If you have any doubt about a date (for example, you suspect other sources differ but could not open them), omit it and explain in `unverified`.

## Sources (work efficiently: one or two strong pages per person that cover several fields)
- Good sources: official state, royal-house, parliament or government pages; national biography dictionaries (Deutsche Biographie, Svenskt biografiskt lexikon, lex.dk, snl.no, parlement.com, historisches-lexikon.li, vle.lt, Dictionary of Irish Biography, Real Academia de la Historia historia-hispanica.rah.es); Encyclopaedia Iranica; Gale reference entries on encyclopedia.com (type them `official_history`); national archives and libraries.
- Library of Congress authority records (id.loc.gov) can support birth and death years. If the html page is blocked, use `.madsrdf.json`, but keep the normal URL as `url`.
- Wikidata is for the Q-id only, and never a source. Wikipedia and Baidu are never sources.
- If an authority record (LoC, BnF and similar) says its own data came from Wikipedia, do not use that record for that fact.
- Each cited page must be fetched today. Give a verbatim excerpt of 25 words or fewer, a precise locator, and `accessedOn` "2026-11-07".
- Conflicting sources go to `conflicts` with no value. Anything unconfirmed is omitted and listed in `unverified`. Never fill from memory.
- The summary is 1–2 neutral sentences in your own words, using only facts in the cited sources. For controversial figures, list only the offices held.

## Portrait (optional, at most a few fetches)
- Wikimedia Commons file page only. Both the source-country template and the US template must be PD, CC0, CC BY or CC BY-SA, and the author or source must be stated. Otherwise set it to null.
- `fileUrl` is `https://commons.wikimedia.org/wiki/Special:FilePath/<File>?width=400`.
- Map licences to: pd_expired, us_federal_pd, cc0, cc_by, cc_by_sa.

## Final reply
A short summary covering: who went into people and which fields are missing, who went to staging and why, merges and splits, and unreachable sites.
