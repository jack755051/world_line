using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using WorldLine.Api.Data.Entities;

namespace WorldLine.Api.Data.Configurations;

public class HistoricalEventConfiguration : IEntityTypeConfiguration<HistoricalEvent>
{
    public void Configure(EntityTypeBuilder<HistoricalEvent> builder)
    {
        builder.HasKey(e => e.Id);
        builder.Property(e => e.Id).HasMaxLength(64).ValueGeneratedNever();
        builder.Property(e => e.Name).HasMaxLength(100).IsRequired();
        builder.Property(e => e.ParentEventId).HasMaxLength(64);

        builder.Property(e => e.StartEdtf).HasMaxLength(32).IsRequired();
        builder.Property(e => e.EndEdtf).HasMaxLength(32).IsRequired();
        builder.Property(e => e.StartDecimal).HasColumnType("numeric(8,3)").IsRequired();
        builder.Property(e => e.EndDecimal).HasColumnType("numeric(8,3)").IsRequired();

        builder.Property(e => e.OriginPoint).HasColumnType("geometry(Point,4326)");
        builder.Property(e => e.InfluenceArea).HasColumnType("geometry(MultiPolygon,4326)");
        builder.Property(e => e.Routes).HasColumnType("geometry(MultiLineString,4326)");
        builder.Property(e => e.Sections).HasColumnType("jsonb");

        builder.Property(e => e.CreatedAt).HasDefaultValueSql("now()");
        builder.Property(e => e.UpdatedAt).HasDefaultValueSql("now()");

        // Self-referencing composition edge (big event -> sub-events), also drives semantic zoom.
        builder.HasOne<HistoricalEvent>()
            .WithMany()
            .HasForeignKey(e => e.ParentEventId)
            .OnDelete(DeleteBehavior.Restrict);
    }
}
