using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using WorldLine.Api.Data.Entities;

namespace WorldLine.Api.Data.Configurations;

public class RegimeCitationConfiguration : IEntityTypeConfiguration<RegimeCitation>
{
    public void Configure(EntityTypeBuilder<RegimeCitation> builder)
    {
        builder.HasKey(c => c.Id);
        builder.Property(c => c.Id).HasDefaultValueSql("gen_random_uuid()");
        builder.Property(c => c.EvidenceNote).IsRequired();
        builder.Property(c => c.CreatedAt).HasDefaultValueSql("now()");

        builder.HasOne<Regime>()
            .WithMany()
            .HasForeignKey(c => c.RegimeId)
            .OnDelete(DeleteBehavior.Cascade)
            .IsRequired();

        // Restrict，不是 Cascade——一個 Source 可能被很多筆引用共用，刪掉 Source 前
        // 要先確認沒有任何引用還指著它，不能因為刪一個 Source 就連帶悄悄砍掉一堆
        // 看似無關的政權/疆域/事件引用紀錄。
        builder.HasOne<Source>()
            .WithMany()
            .HasForeignKey(c => c.SourceId)
            .OnDelete(DeleteBehavior.Restrict)
            .IsRequired();
    }
}
