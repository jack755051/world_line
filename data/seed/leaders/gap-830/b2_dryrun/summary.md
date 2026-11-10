# B2 回填 dry-run（不寫入）

- 資料庫：worldline_borders_dev（唯讀連線）；政策版本 bio-2026-11-v0
- 目前 schema：quote 欄 無（migration 未套用）；leader_bio_gaps 表 無（migration 未套用）

| 項目 | 數量 |
|---|---|
| check:quoteNeedsCsharpCheck | 0 |
| conflict:conflict_qualified_field_has_value | 10 |
| db:citations_found_by_seed | 4106 |
| db:citations_of_touched_bios_unmatched | 20 |
| db:citations_total_live | 4319 |
| plan:gap_inserts | 904 |
| plan:gap_inserts_conflict | 74 |
| plan:gap_inserts_identity_uncertain | 7 |
| plan:gap_inserts_not_found | 823 |
| plan:quote_updates | 841 |
| seed:citations | 4106 |
| seed:conflict | 84 |
| seed:not_found | 1062 |
| seed:people | 706 |
| seed:staging | 59 |
| skip:gap_duplicate | 6 |
| skip:gap_field_not_in_vocabulary | 23 |
| skip:quote_over_25 | 3265 |
| skip:unverified_but_field_has_value | 193 |
| skip:unverified_qualified_field_has_value | 43 |
