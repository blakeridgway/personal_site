using System.Diagnostics;
using System.Security.Cryptography;
using System.Text;
using PersonalSite.Models;
using PersonalSite.Services;

namespace PersonalSite.Middleware;

public class TrafficTrackingMiddleware
{
    private readonly RequestDelegate _next;
    private readonly ILogger<TrafficTrackingMiddleware> _logger;

    // Paths to exclude from tracking
    private static readonly HashSet<string> ExcludedPaths = new(StringComparer.OrdinalIgnoreCase)
    {
        "/health",
        "/_framework",
        "/_blazor",
        "/css",
        "/js",
        "/images",
        "/favicon.ico"
    };

    // Extensions to exclude
    private static readonly HashSet<string> ExcludedExtensions = new(StringComparer.OrdinalIgnoreCase)
    {
        ".css", ".js", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".woff", ".woff2", ".ttf", ".map"
    };

    public TrafficTrackingMiddleware(RequestDelegate next, ILogger<TrafficTrackingMiddleware> logger)
    {
        _next = next;
        _logger = logger;
    }

    public async Task InvokeAsync(HttpContext context, ITrafficService trafficService)
    {
        var path = context.Request.Path.Value ?? "/";

        // Check if we should track this request
        if (!ShouldTrack(path))
        {
            await _next(context);
            return;
        }

        // Get or create session ID BEFORE calling next (response hasn't started yet)
        var sessionId = GetOrCreateSessionId(context);
        var ipAddress = GetClientIpAddress(context);
        var userAgent = context.Request.Headers.UserAgent.ToString();
        var referrer = context.Request.Headers.Referer.ToString();
        var method = context.Request.Method;

        var stopwatch = Stopwatch.StartNew();

        try
        {
            await _next(context);
        }
        finally
        {
            stopwatch.Stop();

            try
            {
                var pageView = new PageView
                {
                    IpAddress = ipAddress,
                    UserAgent = userAgent,
                    Path = path,
                    Method = method,
                    Referrer = referrer,
                    Timestamp = DateTime.UtcNow,
                    ResponseTime = stopwatch.ElapsedMilliseconds,
                    StatusCode = context.Response.StatusCode,
                    SessionId = sessionId
                };

                await trafficService.TrackPageViewAsync(pageView);
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error in traffic tracking middleware");
            }
        }
    }

    private static bool ShouldTrack(string path)
    {
        // Check excluded paths
        foreach (var excluded in ExcludedPaths)
        {
            if (path.StartsWith(excluded, StringComparison.OrdinalIgnoreCase))
                return false;
        }

        // Check excluded extensions
        var extension = Path.GetExtension(path);
        if (!string.IsNullOrEmpty(extension) && ExcludedExtensions.Contains(extension))
            return false;

        return true;
    }

    private static string GetClientIpAddress(HttpContext context)
    {
        // Check for forwarded IP (behind proxy/load balancer)
        var forwardedFor = context.Request.Headers["X-Forwarded-For"].FirstOrDefault();
        if (!string.IsNullOrEmpty(forwardedFor))
        {
            var ips = forwardedFor.Split(',', StringSplitOptions.RemoveEmptyEntries);
            if (ips.Length > 0)
                return ips[0].Trim();
        }

        // Check for real IP header
        var realIp = context.Request.Headers["X-Real-IP"].FirstOrDefault();
        if (!string.IsNullOrEmpty(realIp))
            return realIp;

        // Fall back to connection remote IP
        return context.Connection.RemoteIpAddress?.ToString() ?? "unknown";
    }

    private static string GetOrCreateSessionId(HttpContext context)
    {
        const string sessionCookieName = "site_session";

        if (context.Request.Cookies.TryGetValue(sessionCookieName, out var sessionId) && !string.IsNullOrEmpty(sessionId))
        {
            return sessionId;
        }

        // Generate new session ID
        var newSessionId = GenerateSessionId(context);

        context.Response.Cookies.Append(sessionCookieName, newSessionId, new CookieOptions
        {
            HttpOnly = true,
            Secure = true,
            SameSite = SameSiteMode.Lax,
            Expires = DateTimeOffset.UtcNow.AddHours(24)
        });

        return newSessionId;
    }

    private static string GenerateSessionId(HttpContext context)
    {
        var ip = GetClientIpAddress(context);
        var userAgent = context.Request.Headers.UserAgent.ToString();
        var timestamp = DateTime.UtcNow.Ticks.ToString();

        var input = $"{ip}-{userAgent}-{timestamp}-{Guid.NewGuid()}";
        var bytes = MD5.HashData(Encoding.UTF8.GetBytes(input));
        return Convert.ToHexString(bytes);
    }
}

public static class TrafficTrackingMiddlewareExtensions
{
    public static IApplicationBuilder UseTrafficTracking(this IApplicationBuilder builder)
    {
        return builder.UseMiddleware<TrafficTrackingMiddleware>();
    }
}
