using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using WorldLine.Api.Data.Entities;

namespace WorldLine.Api.Data.Configurations;

public class LineagePresetConfiguration : IEntityTypeConfiguration<LineagePreset>
{
    public void Configure(EntityTypeBuilder<LineagePreset> builder)
    {
        builder.HasKey(p => p.Id);
        builder.Property(p => p.Id).HasDefaultValueSql("gen_random_uuid()");
        builder.Property(p => p.PresetName).HasMaxLength(128).IsRequired();
        builder.Property(p => p.CreatedAt).HasDefaultValueSql("now()");
    }
}
