using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using WorldLine.Api.Data.Entities;

namespace WorldLine.Api.Data.Configurations;

public class SourceConfiguration : IEntityTypeConfiguration<Source>
{
    public void Configure(EntityTypeBuilder<Source> builder)
    {
        builder.HasKey(s => s.Id);
        builder.Property(s => s.Id).HasDefaultValueSql("gen_random_uuid()");

        builder.Property(s => s.Title).HasMaxLength(256).IsRequired();
        builder.Property(s => s.AuthorOrPublisher).HasMaxLength(256);
        builder.Property(s => s.VersionOrPublishedAt).HasMaxLength(64);
        builder.Property(s => s.Locator).HasMaxLength(512);
        builder.Property(s => s.License).HasMaxLength(256);
        builder.Property(s => s.CreatedAt).HasDefaultValueSql("now()");
    }
}
