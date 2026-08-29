using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using WorldLine.Api.Data.Entities;

namespace WorldLine.Api.Data.Configurations;

public class RegimeTranslationConfiguration : IEntityTypeConfiguration<RegimeTranslation>
{
    public void Configure(EntityTypeBuilder<RegimeTranslation> builder)
    {
        builder.HasKey(t => t.Id);
        builder.Property(t => t.Id).HasDefaultValueSql("gen_random_uuid()");

        builder.Property(t => t.Locale).HasMaxLength(5).IsRequired();
        builder.Property(t => t.SelfName).HasMaxLength(128).IsRequired();
        builder.Property(t => t.CreatedAt).HasDefaultValueSql("now()");

        builder.HasOne<Regime>()
            .WithMany()
            .HasForeignKey(t => t.RegimeId)
            .OnDelete(DeleteBehavior.Cascade)
            .IsRequired();

        builder.HasIndex(t => new { t.RegimeId, t.Locale }).IsUnique();
    }
}
