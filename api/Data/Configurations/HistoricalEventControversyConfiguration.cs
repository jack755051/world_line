using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using WorldLine.Api.Data.Entities;

namespace WorldLine.Api.Data.Configurations;

public class HistoricalEventControversyConfiguration : IEntityTypeConfiguration<HistoricalEventControversy>
{
    public void Configure(EntityTypeBuilder<HistoricalEventControversy> builder)
    {
        builder.HasKey(c => c.Id);
        builder.Property(c => c.Id).HasDefaultValueSql("gen_random_uuid()");
        builder.Property(c => c.EventId).HasMaxLength(64);
        builder.Property(c => c.Topic).HasMaxLength(128).IsRequired();
        builder.Property(c => c.NeutralDescription).IsRequired();
        builder.Property(c => c.Viewpoints).HasColumnType("jsonb");

        builder.HasOne<HistoricalEvent>()
            .WithMany()
            .HasForeignKey(c => c.EventId)
            .OnDelete(DeleteBehavior.Cascade);
    }
}
