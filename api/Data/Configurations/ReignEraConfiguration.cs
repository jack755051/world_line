using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using WorldLine.Api.Data.Entities;

namespace WorldLine.Api.Data.Configurations;

public class ReignEraConfiguration : IEntityTypeConfiguration<ReignEra>
{
    public void Configure(EntityTypeBuilder<ReignEra> builder)
    {
        builder.HasKey(e => e.Id);
        builder.Property(e => e.Id).HasDefaultValueSql("gen_random_uuid()");
        builder.Property(e => e.EraName).HasMaxLength(64).IsRequired();
        builder.Property(e => e.CreatedAt).HasDefaultValueSql("now()");

        builder.HasOne<Regime>()
            .WithMany()
            .HasForeignKey(e => e.RegimeId)
            .OnDelete(DeleteBehavior.Restrict)
            .IsRequired();
    }
}
