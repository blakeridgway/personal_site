using Microsoft.EntityFrameworkCore;
using PersonalSite.Models;

namespace PersonalSite.Data;

public class ApplicationDbContext : DbContext
{
    public ApplicationDbContext(DbContextOptions<ApplicationDbContext> options)
        : base(options)
    {
    }

    public DbSet<PageView> PageViews => Set<PageView>();
    public DbSet<UniqueVisitor> UniqueVisitors => Set<UniqueVisitor>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        modelBuilder.Entity<PageView>(entity =>
        {
            entity.HasIndex(e => e.IpAddress);
            entity.HasIndex(e => e.Path);
            entity.HasIndex(e => e.Timestamp);
            entity.HasIndex(e => e.SessionId);
        });

        modelBuilder.Entity<UniqueVisitor>(entity =>
        {
            entity.HasIndex(e => new { e.IpAddress, e.UserAgentHash }).IsUnique();
            entity.HasIndex(e => e.LastVisit);
        });
    }
}
