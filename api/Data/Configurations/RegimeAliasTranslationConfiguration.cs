using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using WorldLine.Api.Data.Entities;

namespace WorldLine.Api.Data.Configurations;

public class RegimeAliasTranslationConfiguration : IEntityTypeConfiguration<RegimeAliasTranslation>
{
    public void Configure(EntityTypeBuilder<RegimeAliasTranslation> builder)
    {
        builder.HasKey(t => t.Id);
        builder.Property(t => t.Id).HasDefaultValueSql("gen_random_uuid()");

        builder.Property(t => t.Locale).HasMaxLength(5).IsRequired();
        builder.Property(t => t.AliasName).HasMaxLength(128).IsRequired();
        builder.Property(t => t.CreatedAt).HasDefaultValueSql("now()");

        builder.HasOne<RegimeAlias>()
            .WithMany()
            .HasForeignKey(t => t.RegimeAliasId)
            .OnDelete(DeleteBehavior.Cascade)
            .IsRequired();

        builder.HasIndex(t => new { t.RegimeAliasId, t.Locale }).IsUnique();
    }
}
