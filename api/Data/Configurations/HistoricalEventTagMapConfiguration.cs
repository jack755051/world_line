using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using WorldLine.Api.Data.Entities;

namespace WorldLine.Api.Data.Configurations;

public class HistoricalEventTagMapConfiguration : IEntityTypeConfiguration<HistoricalEventTagMap>
{
    public void Configure(EntityTypeBuilder<HistoricalEventTagMap> builder)
    {
        // PRD SQL table name is singular "historical_event_tag_map" — override the
        // naming-convention-derived plural that would come from the DbSet name.
        builder.ToTable("historical_event_tag_map");
        builder.HasKey(m => new { m.EventId, m.TagId });
        builder.Property(m => m.EventId).HasMaxLength(64);

        builder.HasOne<HistoricalEvent>()
            .WithMany()
            .HasForeignKey(m => m.EventId)
            .OnDelete(DeleteBehavior.Cascade)
            .IsRequired();

        builder.HasOne<EventTag>()
            .WithMany()
            .HasForeignKey(m => m.TagId)
            .OnDelete(DeleteBehavior.Cascade)
            .IsRequired();
    }
}
