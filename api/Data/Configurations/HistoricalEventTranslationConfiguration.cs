using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using WorldLine.Api.Data.Entities;

namespace WorldLine.Api.Data.Configurations;

public class HistoricalEventTranslationConfiguration : IEntityTypeConfiguration<HistoricalEventTranslation>
{
    public void Configure(EntityTypeBuilder<HistoricalEventTranslation> builder)
    {
        builder.HasKey(t => t.Id);
        builder.Property(t => t.Id).HasDefaultValueSql("gen_random_uuid()");

        builder.Property(t => t.EventId).HasMaxLength(64).IsRequired();
        builder.Property(t => t.Locale).HasMaxLength(5).IsRequired();
        builder.Property(t => t.Name).HasMaxLength(100).IsRequired();
        builder.Property(t => t.CreatedAt).HasDefaultValueSql("now()");

        builder.HasOne<HistoricalEvent>()
            .WithMany()
            .HasForeignKey(t => t.EventId)
            .OnDelete(DeleteBehavior.Cascade)
            .IsRequired();

        builder.HasIndex(t => new { t.EventId, t.Locale }).IsUnique();
    }
}
