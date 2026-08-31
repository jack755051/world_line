using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using WorldLine.Api.Data.Entities;

namespace WorldLine.Api.Data.Configurations;

public class HistoricalEventCitationConfiguration : IEntityTypeConfiguration<HistoricalEventCitation>
{
    public void Configure(EntityTypeBuilder<HistoricalEventCitation> builder)
    {
        builder.HasKey(c => c.Id);
        builder.Property(c => c.Id).HasDefaultValueSql("gen_random_uuid()");
        builder.Property(c => c.HistoricalEventId).HasMaxLength(64).IsRequired();
        builder.Property(c => c.EvidenceNote).IsRequired();
        builder.Property(c => c.CreatedAt).HasDefaultValueSql("now()");

        builder.HasOne<HistoricalEvent>()
            .WithMany()
            .HasForeignKey(c => c.HistoricalEventId)
            .OnDelete(DeleteBehavior.Cascade)
            .IsRequired();

        builder.HasOne<Source>()
            .WithMany()
            .HasForeignKey(c => c.SourceId)
            .OnDelete(DeleteBehavior.Restrict)
            .IsRequired();
    }
}
