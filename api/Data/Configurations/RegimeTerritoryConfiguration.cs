using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using WorldLine.Api.Data.Entities;

namespace WorldLine.Api.Data.Configurations;

public class RegimeTerritoryConfiguration : IEntityTypeConfiguration<RegimeTerritory>
{
    public void Configure(EntityTypeBuilder<RegimeTerritory> builder)
    {
        builder.HasKey(t => t.Id);
        builder.Property(t => t.Id).HasDefaultValueSql("gen_random_uuid()");

        // I1: valid_period is required (year-precision int4range, see PRD §6 設計原則).
        builder.Property(t => t.ValidPeriod).HasColumnType("int4range").IsRequired();
        builder.Property(t => t.Geom).HasColumnType("geometry(MultiPolygon,4326)").IsRequired();
        builder.Property(t => t.IsDisputed).HasDefaultValue(false);
        builder.Property(t => t.CreatedAt).HasDefaultValueSql("now()");
        builder.Property(t => t.Version).HasDefaultValue(0);

        builder.HasOne<Regime>()
            .WithMany()
            .HasForeignKey(t => t.RegimeId)
            .OnDelete(DeleteBehavior.Restrict)
            .IsRequired();

        // I5: correction chain — points to the replacement row, original is never deleted/overwritten.
        builder.HasOne<RegimeTerritory>()
            .WithMany()
            .HasForeignKey(t => t.SupersededBy)
            .OnDelete(DeleteBehavior.Restrict);
    }
}
