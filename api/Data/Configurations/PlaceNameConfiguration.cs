using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using WorldLine.Api.Data.Entities;

namespace WorldLine.Api.Data.Configurations;

public class PlaceNameConfiguration : IEntityTypeConfiguration<PlaceName>
{
    public void Configure(EntityTypeBuilder<PlaceName> builder)
    {
        builder.HasKey(p => p.Id);
        builder.Property(p => p.Id).HasDefaultValueSql("gen_random_uuid()");
        builder.Property(p => p.HistoricalName).HasMaxLength(128).IsRequired();
        builder.Property(p => p.ModernName).HasMaxLength(128);
        builder.Property(p => p.ValidPeriod).HasColumnType("int4range");
        builder.Property(p => p.Geom).HasColumnType("geometry(Point,4326)");
        builder.Property(p => p.CreatedAt).HasDefaultValueSql("now()");
    }
}
