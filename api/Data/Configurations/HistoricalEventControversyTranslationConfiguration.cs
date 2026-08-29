using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using WorldLine.Api.Data.Entities;

namespace WorldLine.Api.Data.Configurations;

public class HistoricalEventControversyTranslationConfiguration : IEntityTypeConfiguration<HistoricalEventControversyTranslation>
{
    public void Configure(EntityTypeBuilder<HistoricalEventControversyTranslation> builder)
    {
        builder.HasKey(t => t.Id);
        builder.Property(t => t.Id).HasDefaultValueSql("gen_random_uuid()");

        builder.Property(t => t.Locale).HasMaxLength(5).IsRequired();
        builder.Property(t => t.Topic).HasMaxLength(128).IsRequired();
        builder.Property(t => t.CreatedAt).HasDefaultValueSql("now()");

        builder.HasOne<HistoricalEventControversy>()
            .WithMany()
            .HasForeignKey(t => t.ControversyId)
            .OnDelete(DeleteBehavior.Cascade)
            .IsRequired();

        builder.HasIndex(t => new { t.ControversyId, t.Locale }).IsUnique();
    }
}
