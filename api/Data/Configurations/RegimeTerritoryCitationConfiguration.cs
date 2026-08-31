using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using WorldLine.Api.Data.Entities;

namespace WorldLine.Api.Data.Configurations;

public class RegimeTerritoryCitationConfiguration : IEntityTypeConfiguration<RegimeTerritoryCitation>
{
    public void Configure(EntityTypeBuilder<RegimeTerritoryCitation> builder)
    {
        builder.HasKey(c => c.Id);
        builder.Property(c => c.Id).HasDefaultValueSql("gen_random_uuid()");
        builder.Property(c => c.EvidenceNote).IsRequired();
        builder.Property(c => c.CreatedAt).HasDefaultValueSql("now()");

        builder.HasOne<RegimeTerritory>()
            .WithMany()
            .HasForeignKey(c => c.RegimeTerritoryId)
            .OnDelete(DeleteBehavior.Cascade)
            .IsRequired();

        // Restrict，理由同 RegimeCitationConfiguration。
        builder.HasOne<Source>()
            .WithMany()
            .HasForeignKey(c => c.SourceId)
            .OnDelete(DeleteBehavior.Restrict)
            .IsRequired();
    }
}
