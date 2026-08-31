using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using WorldLine.Api.Data.Entities;

namespace WorldLine.Api.Data.Configurations;

public class RegimeRelationCitationConfiguration : IEntityTypeConfiguration<RegimeRelationCitation>
{
    public void Configure(EntityTypeBuilder<RegimeRelationCitation> builder)
    {
        builder.HasKey(c => c.Id);
        builder.Property(c => c.Id).HasDefaultValueSql("gen_random_uuid()");
        builder.Property(c => c.EvidenceNote).IsRequired();
        builder.Property(c => c.CreatedAt).HasDefaultValueSql("now()");

        builder.HasOne<RegimeRelation>()
            .WithMany()
            .HasForeignKey(c => c.RegimeRelationId)
            .OnDelete(DeleteBehavior.Cascade)
            .IsRequired();

        builder.HasOne<Source>()
            .WithMany()
            .HasForeignKey(c => c.SourceId)
            .OnDelete(DeleteBehavior.Restrict)
            .IsRequired();
    }
}
