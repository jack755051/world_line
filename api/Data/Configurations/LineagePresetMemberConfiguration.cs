using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using WorldLine.Api.Data.Entities;

namespace WorldLine.Api.Data.Configurations;

public class LineagePresetMemberConfiguration : IEntityTypeConfiguration<LineagePresetMember>
{
    public void Configure(EntityTypeBuilder<LineagePresetMember> builder)
    {
        builder.HasKey(m => new { m.PresetId, m.RegimeId });

        builder.HasOne<LineagePreset>()
            .WithMany()
            .HasForeignKey(m => m.PresetId)
            .OnDelete(DeleteBehavior.Cascade)
            .IsRequired();

        builder.HasOne<Regime>()
            .WithMany()
            .HasForeignKey(m => m.RegimeId)
            .OnDelete(DeleteBehavior.Restrict)
            .IsRequired();
    }
}
