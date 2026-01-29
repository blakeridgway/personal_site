using PersonalSite.Models;

namespace PersonalSite.Services;

public interface ITrafficService
{
    Task TrackPageViewAsync(PageView pageView);
    Task<TrafficStats> GetStatsAsync(int days = 30);
    Task<IEnumerable<PageViewSummary>> GetTopPagesAsync(int days = 30, int count = 10);
    Task<IEnumerable<ReferrerSummary>> GetTopReferrersAsync(int days = 30, int count = 10);
    Task<IEnumerable<DailyTraffic>> GetDailyTrafficAsync(int days = 30);
    Task<IEnumerable<PageView>> GetRecentPageViewsAsync(int count = 20);
}
