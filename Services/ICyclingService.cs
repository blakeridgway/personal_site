using PersonalSite.Models;

namespace PersonalSite.Services;

public interface ICyclingService
{
    Task<CyclingStats> GetYtdStatsAsync();
    Task<IEnumerable<CyclingActivity>> GetRecentActivitiesAsync(int count = 5);
    bool IsAvailable { get; }
}
