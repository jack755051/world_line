using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using WorldLine.Api.Data.Entities;

namespace WorldLine.Api.Data.Configurations;

public class EventTagConfiguration : IEntityTypeConfiguration<EventTag>
{
    public void Configure(EntityTypeBuilder<EventTag> builder)
    {
        builder.HasKey(t => t.Id);
        builder.Property(t => t.TagName).HasMaxLength(32).IsRequired();
        builder.HasIndex(t => t.TagName).IsUnique();
    }
}
