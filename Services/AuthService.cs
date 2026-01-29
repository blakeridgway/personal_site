using System.Security.Claims;
using System.Security.Cryptography;
using System.Text;
using Microsoft.Extensions.Options;

namespace PersonalSite.Services;

public interface IAuthService
{
    Task<ClaimsPrincipal?> AuthenticateAsync(string username, string password);
    bool ValidateCredentials(string username, string password);
}

public class AuthService : IAuthService
{
    private readonly AdminOptions _options;
    private readonly ILogger<AuthService> _logger;

    public AuthService(IOptions<AdminOptions> options, ILogger<AuthService> logger)
    {
        _options = options.Value;
        _logger = logger;
    }

    public Task<ClaimsPrincipal?> AuthenticateAsync(string username, string password)
    {
        if (!ValidateCredentials(username, password))
        {
            return Task.FromResult<ClaimsPrincipal?>(null);
        }

        var claims = new List<Claim>
        {
            new(ClaimTypes.Name, username),
            new(ClaimTypes.Role, "Admin")
        };

        var identity = new ClaimsIdentity(claims, "CookieAuth");
        var principal = new ClaimsPrincipal(identity);

        _logger.LogInformation("User {Username} authenticated successfully", username);

        return Task.FromResult<ClaimsPrincipal?>(principal);
    }

    public bool ValidateCredentials(string username, string password)
    {
        if (string.IsNullOrEmpty(_options.Username) || string.IsNullOrEmpty(_options.PasswordHash))
        {
            _logger.LogWarning("Admin credentials not configured");
            return false;
        }

        if (!username.Equals(_options.Username, StringComparison.OrdinalIgnoreCase))
        {
            return false;
        }

        var passwordHash = ComputeHash(password);
        return passwordHash.Equals(_options.PasswordHash, StringComparison.OrdinalIgnoreCase);
    }

    private static string ComputeHash(string input)
    {
        var bytes = SHA256.HashData(Encoding.UTF8.GetBytes(input));
        return Convert.ToHexString(bytes);
    }
}

public class AdminOptions
{
    public string Username { get; set; } = string.Empty;
    public string PasswordHash { get; set; } = string.Empty;
}
