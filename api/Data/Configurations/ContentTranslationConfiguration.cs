using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using WorldLine.Api.Data.Entities;

namespace WorldLine.Api.Data.Configurations;

public class ContentTranslationConfiguration : IEntityTypeConfiguration<ContentTranslation>
{
    public void Configure(EntityTypeBuilder<ContentTranslation> builder)
    {
        builder.HasKey(t => t.Id);
        builder.Property(t => t.Id).HasDefaultValueSql("gen_random_uuid()");

        builder.Property(t => t.EntityType).HasMaxLength(64).IsRequired();
        builder.Property(t => t.EntityId).HasMaxLength(64).IsRequired();
        builder.Property(t => t.FieldName).HasMaxLength(64).IsRequired();
        builder.Property(t => t.Locale).HasMaxLength(5).IsRequired();
        builder.Property(t => t.TranslatedText).IsRequired();
        builder.Property(t => t.CreatedAt).HasDefaultValueSql("now()");

        // 複合唯一鍵同時也是查詢用的複合索引（涵蓋「查某實體某語言的翻譯」這個主要查詢模式）。
        builder.HasIndex(t => new { t.EntityType, t.EntityId, t.FieldName, t.Locale }).IsUnique();
    }
}
