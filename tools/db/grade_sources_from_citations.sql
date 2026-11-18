-- 把來源等級回填到 sources.grade（docs/source-rules.md §2：等級屬於來源本身）。
-- 只用「已經有人評過」的資訊，不依來源種類猜：
--   1. 該來源在各 citation 表的評等一致 → 沿用。
--   2. 評等不一致 → 先取較低的一級，並在依據裡寫明，待複核。
--   3. 條約原文（source_kind = 'treaty'）→ A。
-- 其餘維持 NULL（尚未評等），由考證逐一評。只處理 grade 仍是 NULL 的來源，可重跑。
-- 用法：由呼叫端包在交易裡（先 ROLLBACK 預演，再 COMMIT）。
WITH g AS (
  SELECT source_id, grade FROM leader_bio_field_citations WHERE grade IS NOT NULL AND retracted_at IS NULL
  UNION ALL SELECT source_id, grade FROM leader_bio_paragraph_citations WHERE grade IS NOT NULL
  UNION ALL SELECT source_id, grade FROM person_position_citations WHERE grade IS NOT NULL
  UNION ALL SELECT source_id, grade FROM person_role_citations WHERE grade IS NOT NULL
  UNION ALL SELECT source_id, grade FROM leader_record_citations WHERE grade IS NOT NULL AND retracted_at IS NULL
  UNION ALL SELECT source_id, grade FROM battle_profile_citations
  UNION ALL SELECT source_id, grade FROM battle_phase_citations
  UNION ALL SELECT source_id, grade FROM battle_map_feature_citations
  UNION ALL SELECT source_id, grade FROM battle_unit_citations
), per AS (
  SELECT source_id, array_agg(DISTINCT grade ORDER BY grade) AS gs, count(*) AS n FROM g GROUP BY 1
)
UPDATE sources s
SET grade = per.gs[array_length(per.gs, 1)],
    grade_basis = CASE WHEN array_length(per.gs, 1) = 1
                       THEN '沿用既有引文的評等（' || per.n || ' 筆引文一致；2026-11-13 回填）'
                       ELSE '既有引文的評等不一致（' || array_to_string(per.gs, '、') || '），先取較低的一級，待複核（2026-11-13 回填）' END,
    updated_at = now(), version = s.version + 1
FROM per
WHERE per.source_id = s.id AND s.grade IS NULL;

UPDATE sources
SET grade = 'A', grade_basis = '條約原文（source_kind = treaty；2026-11-13 回填）', updated_at = now(), version = version + 1
WHERE grade IS NULL AND source_kind = 'treaty';
