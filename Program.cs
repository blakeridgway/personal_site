using System.Xml.Linq;
using Microsoft.AspNetCore.Authentication;
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

// Auth endpoints
app.MapPost("/api/auth/login", async (HttpContext context, IAuthService authService) =>
{
    var form = await context.Request.ReadFormAsync();
    var username = form["username"].ToString();
    var password = form["password"].ToString();

    var principal = await authService.AuthenticateAsync(username, password);

    if (principal != null)
    {
        await context.SignInAsync(
            CookieAuthenticationDefaults.AuthenticationScheme,
            principal,
            new Microsoft.AspNetCore.Authentication.AuthenticationProperties
            {
                IsPersistent = true,
                ExpiresUtc = DateTimeOffset.UtcNow.AddHours(24)
            });
        context.Response.Redirect("/admin");
    }
    else
    {
        context.Response.Redirect("/admin/login?error=invalid");
    }
});

app.MapGet("/admin/logout", async (HttpContext context) =>
{
    await context.SignOutAsync(CookieAuthenticationDefaults.AuthenticationScheme);
    context.Response.Redirect("/");
});

// RSS Feed endpoint
app.MapGet("/feed.xml", async (HttpContext context, IBlogService blogService) =>
{
    var posts = await blogService.GetAllPostsAsync();
    var baseUrl = $"{context.Request.Scheme}://{context.Request.Host}";

    XNamespace atom = "http://www.w3.org/2005/Atom";
    var rss = new XDocument(
        new XDeclaration("1.0", "utf-8", null),
        new XElement("rss",
            new XAttribute("version", "2.0"),
            new XAttribute(XNamespace.Xmlns + "atom", atom),
            new XElement("channel",
                new XElement("title", "Blake Ridgway"),
                new XElement("link", baseUrl),
                new XElement("description", "SRE practices, cloud infrastructure, DevOps automation, and cycling."),
                new XElement("language", "en-us"),
                new XElement(atom + "link",
                    new XAttribute("href", $"{baseUrl}/feed.xml"),
                    new XAttribute("rel", "self"),
                    new XAttribute("type", "application/rss+xml")),
                new XElement("lastBuildDate", DateTime.UtcNow.ToString("R")),
                posts.Select(post => new XElement("item",
                    new XElement("title", post.Title),
                    new XElement("link", $"{baseUrl}/blog/{post.Slug}"),
                    new XElement("guid", $"{baseUrl}/blog/{post.Slug}"),
                    new XElement("description", post.Excerpt),
                    new XElement("pubDate", post.PublishedDate.ToUniversalTime().ToString("R")),
                    new XElement("category", post.Category),
                    new XElement("author", post.Author)
                ))
            )
        )
    );

    context.Response.ContentType = "application/rss+xml; charset=utf-8";
    await context.Response.WriteAsync(rss.Declaration + rss.ToString());
});

// Sitemap endpoint
app.MapGet("/sitemap.xml", async (HttpContext context, IBlogService blogService) =>
{
    var posts = await blogService.GetAllPostsAsync();
    var baseUrl = $"{context.Request.Scheme}://{context.Request.Host}";

    XNamespace ns = "http://www.sitemaps.org/schemas/sitemap/0.9";
    var sitemap = new XDocument(
        new XDeclaration("1.0", "utf-8", null),
        new XElement(ns + "urlset",
            // Static pages
            new XElement(ns + "url",
                new XElement(ns + "loc", baseUrl + "/"),
                new XElement(ns + "changefreq", "weekly"),
                new XElement(ns + "priority", "1.0")),
            new XElement(ns + "url",
                new XElement(ns + "loc", baseUrl + "/about"),
                new XElement(ns + "changefreq", "monthly"),
                new XElement(ns + "priority", "0.8")),
            new XElement(ns + "url",
                new XElement(ns + "loc", baseUrl + "/blog"),
                new XElement(ns + "changefreq", "weekly"),
                new XElement(ns + "priority", "0.9")),
            new XElement(ns + "url",
                new XElement(ns + "loc", baseUrl + "/biking"),
                new XElement(ns + "changefreq", "daily"),
                new XElement(ns + "priority", "0.7")),
            new XElement(ns + "url",
                new XElement(ns + "loc", baseUrl + "/hardware"),
                new XElement(ns + "changefreq", "monthly"),
                new XElement(ns + "priority", "0.6")),
            // Blog posts
            posts.Select(post => new XElement(ns + "url",
                new XElement(ns + "loc", $"{baseUrl}/blog/{post.Slug}"),
                new XElement(ns + "lastmod", post.PublishedDate.ToString("yyyy-MM-dd")),
                new XElement(ns + "changefreq", "monthly"),
                new XElement(ns + "priority", "0.7")
            ))
        )
    );

    context.Response.ContentType = "application/xml; charset=utf-8";
    await context.Response.WriteAsync(sitemap.Declaration + sitemap.ToString());
});

app.MapRazorComponents<App>()
    .AddInteractiveServerRenderMode();

app.Run();
