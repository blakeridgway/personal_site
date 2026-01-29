using System.ComponentModel.DataAnnotations;

namespace PersonalSite.Models;

public class PageView
{
    public int Id { get; set; }

    [MaxLength(45)]
    public string IpAddress { get; set; } = string.Empty;

    public string? UserAgent { get; set; }

    [MaxLength(255)]
    public string Path { get; set; } = string.Empty;

    [MaxLength(10)]
    public string Method { get; set; } = string.Empty;

    [MaxLength(500)]
    public string? Referrer { get; set; }

    public DateTime Timestamp { get; set; } = DateTime.UtcNow;

    public double ResponseTime { get; set; }

    public int StatusCode { get; set; }

    [MaxLength(2)]
    public string? Country { get; set; }

    [MaxLength(100)]
    public string? City { get; set; }

    [MaxLength(255)]
    public string? SessionId { get; set; }
}

public class UniqueVisitor
{
    public int Id { get; set; }

    [MaxLength(45)]
    public string IpAddress { get; set; } = string.Empty;

    [MaxLength(64)]
    public string UserAgentHash { get; set; } = string.Empty;

    public DateTime FirstVisit { get; set; } = DateTime.UtcNow;

    public DateTime LastVisit { get; set; } = DateTime.UtcNow;

    public int VisitCount { get; set; } = 1;

    [MaxLength(2)]
    public string? Country { get; set; }

    [MaxLength(100)]
    public string? City { get; set; }
}

public class TrafficStats
{
    public int TotalPageViews { get; set; }
    public int UniqueVisitors { get; set; }
    public double AvgResponseTime { get; set; }
    public double BounceRate { get; set; }
}

public class DailyTraffic
{
    public DateTime Date { get; set; }
    public int PageViews { get; set; }
    public int UniqueVisitors { get; set; }
}

public class PageViewSummary
{
    public string Path { get; set; } = string.Empty;
    public int Views { get; set; }
}

public class ReferrerSummary
{
    public string Referrer { get; set; } = string.Empty;
    public int Count { get; set; }
}
