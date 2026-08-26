using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using WorldLine.Api.Data.Entities;

namespace WorldLine.Api.Data.Configurations;

public class ObserverCategoryConfiguration : IEntityTypeConfiguration<ObserverCategory>
{
    public void Configure(EntityTypeBuilder<ObserverCategory> builder)
    {
        builder.HasKey(c => c.Id);
        builder.Property(c => c.CategoryName).HasMaxLength(64).IsRequired();
        builder.HasIndex(c => c.CategoryName).IsUnique();
    }
}
