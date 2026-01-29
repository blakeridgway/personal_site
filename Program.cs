using Microsoft.AspNetCore.Authentication.Cookies;
using Microsoft.EntityFrameworkCore;
using PersonalSite.Components;
using PersonalSite.Data;
using PersonalSite.Middleware;
using PersonalSite.Models;
using PersonalSite.Services;

var builder = WebApplication.CreateBuilder(args);

// Add services to the container.
builder.Services.AddRazorComponents()
    .AddInteractiveServerComponents();

// Add memory cache
builder.Services.AddMemoryCache();

// Add EF Core with SQLite
builder.Services.AddDbContext<ApplicationDbContext>(options =>
    options.UseSqlite(builder.Configuration.GetConnectionString("DefaultConnection")
        ?? "Data Source=traffic.db"));

// Add authentication
builder.Services.AddAuthentication(CookieAuthenticationDefaults.AuthenticationScheme)
    .AddCookie(options =>
    {
        options.LoginPath = "/admin/login";
        options.LogoutPath = "/admin/logout";
        options.ExpireTimeSpan = TimeSpan.FromHours(24);
        options.SlidingExpiration = true;
        options.Cookie.HttpOnly = true;
        options.Cookie.SecurePolicy = CookieSecurePolicy.SameAsRequest;
    });
builder.Services.AddAuthorization();
builder.Services.AddCascadingAuthenticationState();
builder.Services.AddHttpContextAccessor();

// Configure admin options
builder.Services.Configure<AdminOptions>(builder.Configuration.GetSection("Admin"));
builder.Services.AddScoped<IAuthService, AuthService>();

// Add custom services
builder.Services.AddScoped<IBlogService, BlogService>();
builder.Services.AddScoped<ITrafficService, TrafficService>();

// Configure Intervals.icu service
builder.Services.Configure<IntervalsIcuOptions>(
    builder.Configuration.GetSection("IntervalsIcu"));
builder.Services.AddHttpClient<ICyclingService, IntervalsIcuService>();

// Add health checks
builder.Services.AddHealthChecks();

var app = builder.Build();

// Ensure database is created
using (var scope = app.Services.CreateScope())
{
    var db = scope.ServiceProvider.GetRequiredService<ApplicationDbContext>();
    db.Database.EnsureCreated();
}

// Configure the HTTP request pipeline.
if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler("/Error", createScopeForErrors: true);
}

app.UseStaticFiles();

// Add traffic tracking middleware
app.UseTrafficTracking();

app.UseAuthentication();
app.UseAuthorization();

app.UseAntiforgery();

// Health check endpoint
app.MapHealthChecks("/health");

app.MapRazorComponents<App>()
    .AddInteractiveServerRenderMode();

app.Run();
