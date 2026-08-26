using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using WorldLine.Api.Data.Entities;

namespace WorldLine.Api.Data.Configurations;

public class RegimeConfiguration : IEntityTypeConfiguration<Regime>
{
    public void Configure(EntityTypeBuilder<Regime> builder)
    {
        builder.HasKey(r => r.Id);
        builder.Property(r => r.Id).HasDefaultValueSql("gen_random_uuid()");
        builder.Property(r => r.SelfName).HasMaxLength(128).IsRequired();
        builder.Property(r => r.Status).HasMaxLength(32).IsRequired();
        builder.Property(r => r.OriginTransitionType).HasMaxLength(16);
        builder.Property(r => r.CreatedAt).HasDefaultValueSql("now()");
        builder.Property(r => r.UpdatedAt).HasDefaultValueSql("now()");
        builder.Property(r => r.Version).HasDefaultValue(0);

        // Self-referencing transition edges — Restrict to avoid multiple-cascade-path errors.
        builder.HasOne<Regime>()
            .WithMany()
            .HasForeignKey(r => r.PredecessorRegimeId)
            .OnDelete(DeleteBehavior.Restrict);

        builder.HasOne<Regime>()
            .WithMany()
            .HasForeignKey(r => r.DestroyedByRegimeId)
            .OnDelete(DeleteBehavior.Restrict);
    }
}
