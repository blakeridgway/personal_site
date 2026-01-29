using System.Security.Cryptography;
using System.Text;
using Microsoft.EntityFrameworkCore;
using PersonalSite.Data;
using PersonalSite.Models;

namespace PersonalSite.Services;

public class TrafficService : ITrafficService
{
    private readonly ApplicationDbContext _context;
    private readonly ILogger<TrafficService> _logger;

    public TrafficService(ApplicationDbContext context, ILogger<TrafficService> logger)
    {
        _context = context;
        _logger = logger;
    }

    public async Task TrackPageViewAsync(PageView pageView)
    {
        try
        {
            // Add page view
            _context.PageViews.Add(pageView);

            // Update or create unique visitor
            var userAgentHash = ComputeHash(pageView.UserAgent ?? "");
            var visitor = await _context.UniqueVisitors
                .FirstOrDefaultAsync(v => v.IpAddress == pageView.IpAddress && v.UserAgentHash == userAgentHash);

            if (visitor == null)
            {
                visitor = new UniqueVisitor
                {
                    IpAddress = pageView.IpAddress,
                    UserAgentHash = userAgentHash,
                    FirstVisit = pageView.Timestamp,
                    LastVisit = pageView.Timestamp,
                    VisitCount = 1,
                    Country = pageView.Country,
                    City = pageView.City
                };
                _context.UniqueVisitors.Add(visitor);
            }
            else
            {
                visitor.LastVisit = pageView.Timestamp;
                visitor.VisitCount++;
            }

            await _context.SaveChangesAsync();
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error tracking page view");
        }
    }

    public async Task<TrafficStats> GetStatsAsync(int days = 30)
    {
        var startDate = DateTime.UtcNow.AddDays(-days);

        var pageViews = await _context.PageViews
            .Where(p => p.Timestamp >= startDate)
            .ToListAsync();

        var uniqueVisitors = await _context.UniqueVisitors
            .Where(v => v.LastVisit >= startDate)
            .CountAsync();

        var avgResponseTime = pageViews.Count > 0
            ? pageViews.Average(p => p.ResponseTime)
            : 0;

        // Calculate bounce rate (single page sessions)
        var sessions = pageViews
            .GroupBy(p => p.SessionId)
            .ToList();

        var bounceRate = sessions.Count > 0
            ? (double)sessions.Count(s => s.Count() == 1) / sessions.Count * 100
            : 0;

        return new TrafficStats
        {
            TotalPageViews = pageViews.Count,
            UniqueVisitors = uniqueVisitors,
            AvgResponseTime = Math.Round(avgResponseTime, 2),
            BounceRate = Math.Round(bounceRate, 1)
        };
    }

    public async Task<IEnumerable<PageViewSummary>> GetTopPagesAsync(int days = 30, int count = 10)
    {
        var startDate = DateTime.UtcNow.AddDays(-days);

        return await _context.PageViews
            .Where(p => p.Timestamp >= startDate)
            .GroupBy(p => p.Path)
            .Select(g => new PageViewSummary
            {
                Path = g.Key,
                Views = g.Count()
            })
            .OrderByDescending(p => p.Views)
            .Take(count)
            .ToListAsync();
    }

    public async Task<IEnumerable<ReferrerSummary>> GetTopReferrersAsync(int days = 30, int count = 10)
    {
        var startDate = DateTime.UtcNow.AddDays(-days);

        return await _context.PageViews
            .Where(p => p.Timestamp >= startDate && !string.IsNullOrEmpty(p.Referrer))
            .GroupBy(p => p.Referrer!)
            .Select(g => new ReferrerSummary
            {
                Referrer = g.Key,
                Count = g.Count()
            })
            .OrderByDescending(r => r.Count)
            .Take(count)
            .ToListAsync();
    }

    public async Task<IEnumerable<DailyTraffic>> GetDailyTrafficAsync(int days = 30)
    {
        var startDate = DateTime.UtcNow.Date.AddDays(-days);

        var pageViews = await _context.PageViews
            .Where(p => p.Timestamp >= startDate)
            .GroupBy(p => p.Timestamp.Date)
            .Select(g => new { Date = g.Key, Views = g.Count(), Sessions = g.Select(x => x.SessionId).Distinct().Count() })
            .OrderBy(d => d.Date)
            .ToListAsync();

        return pageViews.Select(p => new DailyTraffic
        {
            Date = p.Date,
            PageViews = p.Views,
            UniqueVisitors = p.Sessions
        });
    }

    public async Task<IEnumerable<PageView>> GetRecentPageViewsAsync(int count = 20)
    {
        return await _context.PageViews
            .OrderByDescending(p => p.Timestamp)
            .Take(count)
            .ToListAsync();
    }

    private static string ComputeHash(string input)
    {
        var bytes = SHA256.HashData(Encoding.UTF8.GetBytes(input));
        return Convert.ToHexString(bytes)[..16];
    }
}
