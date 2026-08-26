using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using WorldLine.Api.Data.Entities;

namespace WorldLine.Api.Data.Configurations;

public class RegimeRelationConfiguration : IEntityTypeConfiguration<RegimeRelation>
{
    public void Configure(EntityTypeBuilder<RegimeRelation> builder)
    {
        builder.HasKey(r => r.Id);
        builder.Property(r => r.Id).HasDefaultValueSql("gen_random_uuid()");
        builder.Property(r => r.RelationType).HasMaxLength(32).IsRequired();
        builder.Property(r => r.ValidPeriod).HasColumnType("int4range").IsRequired();
        builder.Property(r => r.Route).HasColumnType("geometry(MultiLineString,4326)");
        builder.Property(r => r.CreatedAt).HasDefaultValueSql("now()");

        builder.HasOne<Regime>()
            .WithMany()
            .HasForeignKey(r => r.RegimeAId)
            .OnDelete(DeleteBehavior.Restrict)
            .IsRequired();

        builder.HasOne<Regime>()
            .WithMany()
            .HasForeignKey(r => r.RegimeBId)
            .OnDelete(DeleteBehavior.Restrict)
            .IsRequired();
    }
}
