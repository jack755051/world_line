using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using WorldLine.Api.Domain;

namespace WorldLine.Api.Infrastructure;

/// <summary>
/// 戰役 C1 的 EF 設定（ARCHITECTURE §19.1，2026-11-11）。獨立成檔，WorldLineDbContext 只加一行呼叫。
/// I5 trigger、partial unique index 的撤回條件、GeometryType CHECK 在 migration BattleC1 以 SQL／設定建立。
/// </summary>
internal static class BattleModel
{
    private static string InList(string column, IEnumerable<string> values) =>
        $"{column} IN ({string.Join(", ", values.Select(v => $"'{v}'"))})";

    private static string Retraction => "retracted_at IS NULL OR retraction_reason IS NOT NULL";

    public static void Configure(ModelBuilder b)
    {
        b.Entity<BattleProfile>(e =>
        {
            e.ToTable("battle_profiles", t =>
            {
                t.HasCheckConstraint("ck_battle_profiles_slug", "slug ~ '^[a-z0-9]+([_-][a-z0-9]+)*$'");
                t.HasCheckConstraint("ck_battle_profiles_name_object", "jsonb_typeof(name) = 'object'");
                t.HasCheckConstraint("ck_battle_profiles_objective_object", "jsonb_typeof(objective) = 'object'");
                t.HasCheckConstraint("ck_battle_profiles_control_change_object", "jsonb_typeof(control_change) = 'object'");
                t.HasCheckConstraint("ck_battle_profiles_outcome_text_object", "outcome_text IS NULL OR jsonb_typeof(outcome_text) = 'object'");
                t.HasCheckConstraint("ck_battle_profiles_objective_kind", InList("objective_kind", BattleObjectiveKinds.All));
                t.HasCheckConstraint("ck_battle_profiles_outcome_kind", "outcome_kind IS NULL OR " + InList("outcome_kind", BattleOutcomeKinds.All));
                t.HasCheckConstraint("ck_battle_profiles_status", InList("status", BattleStatuses.All));
                t.HasCheckConstraint("ck_battle_profiles_retraction_reason", Retraction);
            });
            e.HasKey(x => x.EventId);
            e.Property(x => x.Slug).HasMaxLength(64);
            e.Property(x => x.Name).HasColumnType("jsonb");
            e.Property(x => x.Objective).HasColumnType("jsonb");
            e.Property(x => x.ObjectiveKind).HasMaxLength(8);
            e.Property(x => x.TheaterArea).HasColumnType("geometry(MultiPolygon,4326)");
            e.Property(x => x.OutcomeKind).HasMaxLength(16);
            e.Property(x => x.OutcomeText).HasColumnType("jsonb");
            e.Property(x => x.ControlChange).HasColumnType("jsonb");
            e.Property(x => x.Status).HasMaxLength(8).HasDefaultValue(BattleStatuses.Pending);
            e.HasOne<HistoricalEvent>().WithOne().HasForeignKey<BattleProfile>(x => x.EventId).OnDelete(DeleteBehavior.Restrict);
            e.HasOne<ConflictRecord>().WithMany().HasForeignKey(x => x.ConflictRecordId).OnDelete(DeleteBehavior.Restrict);
            e.HasIndex(x => x.Slug).IsUnique();
            e.HasIndex(x => x.TheaterArea).HasMethod("gist");
            Created(e);
        });

        b.Entity<BattlePhase>(e =>
        {
            e.ToTable("battle_phases", t =>
            {
                t.HasCheckConstraint("ck_battle_phases_seq", "seq >= 1");
                t.HasCheckConstraint("ck_battle_phases_name_object", "jsonb_typeof(name) = 'object'");
                t.HasCheckConstraint("ck_battle_phases_summary_object", "summary IS NULL OR jsonb_typeof(summary) = 'object'");
                t.HasCheckConstraint("ck_battle_phases_period_bounded",
                    "NOT isempty(period) AND NOT lower_inf(period) AND NOT upper_inf(period)");
                t.HasCheckConstraint("ck_battle_phases_start_precision", InList("start_precision", DatePrecisions.All));
                t.HasCheckConstraint("ck_battle_phases_end_precision", InList("end_precision", DatePrecisions.All));
                t.HasCheckConstraint("ck_battle_phases_status", InList("status", BattleStatuses.All));
                t.HasCheckConstraint("ck_battle_phases_retraction_reason", Retraction);
            });
            e.Property(x => x.Id).HasDefaultValueSql("gen_random_uuid()");
            e.Property(x => x.Name).HasColumnType("jsonb");
            e.Property(x => x.Period).HasColumnType("daterange");
            e.Property(x => x.StartPrecision).HasMaxLength(8);
            e.Property(x => x.EndPrecision).HasMaxLength(8);
            e.Property(x => x.Summary).HasColumnType("jsonb");
            e.Property(x => x.Status).HasMaxLength(8).HasDefaultValue(BattleStatuses.Pending);
            e.HasOne<BattleProfile>().WithMany().HasForeignKey(x => x.EventId).OnDelete(DeleteBehavior.Restrict);
            // 同一戰役的未撤回階段 seq 唯一（§19.1.2 partial unique）。
            e.HasIndex(x => new { x.EventId, x.Seq }).IsUnique().HasFilter("retracted_at IS NULL");
            Created(e);
        });

        b.Entity<BattleMapFeature>(e =>
        {
            e.ToTable("battle_map_features", t =>
            {
                t.HasCheckConstraint("ck_battle_map_features_feature_key_not_blank", "btrim(feature_key) <> ''");
                t.HasCheckConstraint("ck_battle_map_features_feature_kind", InList("feature_kind", BattleFeatureKinds.All));
                t.HasCheckConstraint("ck_battle_map_features_side_camp", "side_camp IS NULL OR " + InList("side_camp", BattleSideCamps.All));
                t.HasCheckConstraint("ck_battle_map_features_geom_basis", InList("geom_basis", BattleGeomBases.All));
                t.HasCheckConstraint("ck_battle_map_features_status", InList("status", BattleStatuses.All));
                // §19.1.3：derived 不得標 verified。
                t.HasCheckConstraint("ck_battle_map_features_derived_not_verified", "geom_basis <> 'derived' OR status <> 'verified'");
                t.HasCheckConstraint("ck_battle_map_features_geom_srid", "ST_SRID(geom) = 4326");
                t.HasCheckConstraint("ck_battle_map_features_geom_kind",
                    "(feature_kind = 'front' AND GeometryType(geom) IN ('LINESTRING', 'MULTILINESTRING'))"
                    + " OR (feature_kind = 'arrow' AND GeometryType(geom) = 'LINESTRING')"
                    + " OR (feature_kind = 'site' AND GeometryType(geom) = 'POINT')");
                t.HasCheckConstraint("ck_battle_map_features_label_object", "label IS NULL OR jsonb_typeof(label) = 'object'");
                t.HasCheckConstraint("ck_battle_map_features_props_object", "props IS NULL OR jsonb_typeof(props) = 'object'");
                t.HasCheckConstraint("ck_battle_map_features_retraction_reason", Retraction);
            });
            e.Property(x => x.Id).HasDefaultValueSql("gen_random_uuid()");
            e.Property(x => x.FeatureKey).HasMaxLength(96);
            e.Property(x => x.FeatureKind).HasMaxLength(8);
            e.Property(x => x.SideCamp).HasMaxLength(16);
            e.Property(x => x.Geom).HasColumnType("geometry(Geometry,4326)");
            e.Property(x => x.Label).HasColumnType("jsonb");
            e.Property(x => x.Props).HasColumnType("jsonb");
            e.Property(x => x.GeomBasis).HasMaxLength(16);
            e.Property(x => x.Status).HasMaxLength(8).HasDefaultValue(BattleStatuses.Pending);
            e.HasOne<BattlePhase>().WithMany().HasForeignKey(x => x.PhaseId).OnDelete(DeleteBehavior.Restrict);
            e.HasOne<Regime>().WithMany().HasForeignKey(x => x.SideRegimeId).OnDelete(DeleteBehavior.Restrict);
            e.HasIndex(x => x.FeatureKey).IsUnique().HasFilter("retracted_at IS NULL");
            e.HasIndex(x => x.Geom).HasMethod("gist");
            e.HasIndex(x => new { x.PhaseId, x.FeatureKind });
            Created(e);
        });

        b.Entity<BattleUnit>(e =>
        {
            e.ToTable("battle_units", t =>
            {
                t.HasCheckConstraint("ck_battle_units_unit_name_object", "jsonb_typeof(unit_name) = 'object'");
                t.HasCheckConstraint("ck_battle_units_not_own_parent", "parent_unit_id IS NULL OR parent_unit_id <> id");
                t.HasCheckConstraint("ck_battle_units_status", InList("status", BattleStatuses.All));
                t.HasCheckConstraint("ck_battle_units_retraction_reason", Retraction);
            });
            e.Property(x => x.Id).HasDefaultValueSql("gen_random_uuid()");
            e.Property(x => x.UnitName).HasColumnType("jsonb");
            e.Property(x => x.UnitEchelon).HasMaxLength(32);
            e.Property(x => x.Status).HasMaxLength(8).HasDefaultValue(BattleStatuses.Pending);
            e.HasOne<HistoricalEvent>().WithMany().HasForeignKey(x => x.EventId).OnDelete(DeleteBehavior.Restrict);
            e.HasOne<Regime>().WithMany().HasForeignKey(x => x.SideRegimeId).OnDelete(DeleteBehavior.Restrict);
            e.HasOne<BattleUnit>().WithMany().HasForeignKey(x => x.ParentUnitId).OnDelete(DeleteBehavior.Restrict);
            e.HasIndex(x => x.EventId);
            Created(e);
        });

        Citation<BattleProfileCitation>(b, "battle_profile_citations", e =>
        {
            e.Property(x => x.Field).HasMaxLength(16);
            e.HasOne<BattleProfile>().WithMany().HasForeignKey(x => x.EventId).OnDelete(DeleteBehavior.Restrict);
            e.HasIndex(x => x.EventId);
        }, t => t.HasCheckConstraint("ck_battle_profile_citations_field", InList("field", BattleProfileFields.All)));
        Citation<BattlePhaseCitation>(b, "battle_phase_citations", e =>
        {
            e.Property(x => x.ClaimSpan).HasColumnType("int4range");
            e.HasOne<BattlePhase>().WithMany().HasForeignKey(x => x.PhaseId).OnDelete(DeleteBehavior.Restrict);
            e.HasIndex(x => x.PhaseId);
        }, t => t.HasCheckConstraint("ck_battle_phase_citations_claim_span",
            "claim_span IS NULL OR (NOT isempty(claim_span) AND lower(claim_span) >= 0)"));
        Citation<BattleMapFeatureCitation>(b, "battle_map_feature_citations", e =>
        {
            e.HasOne<BattleMapFeature>().WithMany().HasForeignKey(x => x.FeatureId).OnDelete(DeleteBehavior.Restrict);
            e.HasIndex(x => x.FeatureId);
        }, null);
        Citation<BattleUnitCitation>(b, "battle_unit_citations", e =>
        {
            e.HasOne<BattleUnit>().WithMany().HasForeignKey(x => x.UnitId).OnDelete(DeleteBehavior.Restrict);
            e.HasIndex(x => x.UnitId);
        }, null);
    }

    private static void Created<T>(EntityTypeBuilder<T> e) where T : class =>
        e.Property<DateTimeOffset>("CreatedAt").HasDefaultValueSql("now()");

    private static void Citation<T>(ModelBuilder b, string table, Action<EntityTypeBuilder<T>> extra,
        Action<TableBuilder<T>>? extraChecks) where T : BattleCitationBase
    {
        b.Entity<T>(e =>
        {
            e.ToTable(table, t =>
            {
                t.HasCheckConstraint($"ck_{table}_locator_not_blank", "btrim(locator) <> ''");
                t.HasCheckConstraint($"ck_{table}_quote_not_blank", "btrim(quote) <> ''");
                t.HasCheckConstraint($"ck_{table}_grade", InList("grade", BioSourcePolicy.AllowedGrades.Order()));
                t.HasCheckConstraint($"ck_{table}_date_precision", "date_precision IS NULL OR " + InList("date_precision", DatePrecisions.All));
                t.HasCheckConstraint($"ck_{table}_retraction_reason", Retraction);
                extraChecks?.Invoke(t);
            });
            e.Property(x => x.Id).HasDefaultValueSql("gen_random_uuid()");
            e.Property(x => x.QuoteLang).HasMaxLength(35);
            e.Property(x => x.Grade).HasMaxLength(1);
            e.Property(x => x.DatePrecision).HasMaxLength(8);
            e.Property(x => x.PolicyVersion).HasMaxLength(32);
            e.HasOne<Source>().WithMany().HasForeignKey(x => x.SourceId).OnDelete(DeleteBehavior.Restrict);
            extra(e);
            Created(e);
        });
    }
}
