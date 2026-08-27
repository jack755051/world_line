using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using WorldLine.Api.Data.Entities;

namespace WorldLine.Api.Data.Configurations;

public class RegimeTransitionEventConfiguration : IEntityTypeConfiguration<RegimeTransitionEvent>
{
    public void Configure(EntityTypeBuilder<RegimeTransitionEvent> builder)
    {
        builder.ToTable("regime_transition_events");
        builder.HasKey(x => new { x.RegimeId, x.EventId, x.TransitionKind });
        builder.Property(x => x.EventId).HasMaxLength(64);
        builder.Property(x => x.TransitionKind).HasMaxLength(16);

        builder.HasOne<Regime>()
            .WithMany()
            .HasForeignKey(x => x.RegimeId)
            .OnDelete(DeleteBehavior.Cascade)
            .IsRequired();

        builder.HasOne<HistoricalEvent>()
            .WithMany()
            .HasForeignKey(x => x.EventId)
            .OnDelete(DeleteBehavior.Cascade)
            .IsRequired();
    }
}
