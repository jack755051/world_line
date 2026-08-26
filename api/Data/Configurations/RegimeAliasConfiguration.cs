using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using WorldLine.Api.Data.Entities;

namespace WorldLine.Api.Data.Configurations;

public class RegimeAliasConfiguration : IEntityTypeConfiguration<RegimeAlias>
{
    public void Configure(EntityTypeBuilder<RegimeAlias> builder)
    {
        builder.HasKey(a => a.Id);
        builder.Property(a => a.Id).HasDefaultValueSql("gen_random_uuid()");
        builder.Property(a => a.AliasName).HasMaxLength(128).IsRequired();
        builder.Property(a => a.AliasType).HasMaxLength(32);
        builder.Property(a => a.CreatedAt).HasDefaultValueSql("now()");

        // I4: FK is required — an alias can never be orphaned from its canonical regime.
        builder.HasOne<Regime>()
            .WithMany()
            .HasForeignKey(a => a.RegimeId)
            .OnDelete(DeleteBehavior.Restrict)
            .IsRequired();

        builder.HasOne<Regime>()
            .WithMany()
            .HasForeignKey(a => a.ObserverRegimeId)
            .OnDelete(DeleteBehavior.Restrict);
    }
}
