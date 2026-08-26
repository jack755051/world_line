using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using WorldLine.Api.Data.Entities;

namespace WorldLine.Api.Data.Configurations;

public class HistoricalEventPerspectiveConfiguration : IEntityTypeConfiguration<HistoricalEventPerspective>
{
    public void Configure(EntityTypeBuilder<HistoricalEventPerspective> builder)
    {
        builder.HasKey(p => p.Id);
        builder.Property(p => p.Id).HasDefaultValueSql("gen_random_uuid()");
        builder.Property(p => p.EventId).HasMaxLength(64);
        builder.Property(p => p.LocalName).HasMaxLength(128).IsRequired();
        builder.Property(p => p.NarrativeSummary).IsRequired();
        builder.Property(p => p.PrimarySources).HasColumnType("jsonb");
        builder.Property(p => p.ClaimedCasualties).HasColumnType("jsonb");

        builder.HasOne<HistoricalEvent>()
            .WithMany()
            .HasForeignKey(p => p.EventId)
            .OnDelete(DeleteBehavior.Cascade);

        builder.HasOne<Regime>()
            .WithMany()
            .HasForeignKey(p => p.RegimeId)
            .OnDelete(DeleteBehavior.Restrict);

        builder.HasOne<ObserverCategory>()
            .WithMany()
            .HasForeignKey(p => p.ObserverCategoryId)
            .OnDelete(DeleteBehavior.Restrict);
    }
}
