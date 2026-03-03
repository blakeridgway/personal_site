---
title: "How I Built This Site"
slug: how-i-built-this-site
date: 2026-02-07
category: Technology
tags:
  - Blazor
  - .NET
  - Docker
  - Web Development
excerpt: A look at the architecture, tooling, and design decisions behind my personal site — built with ASP.NET Core 8, Blazor, and deployed with Docker.
draft: false
author: Blake Ridgway
---

# How I Built This Site

I've rebuilt my personal site more times than I'd like to admit. Static site generators, WordPress, Hugo — they all worked, but none of them felt like *mine*. This time I wanted something I could extend with real backend logic, not just templated HTML. So I built it with the stack I actually use at work: .NET, containers, and infrastructure I control.

Here's a walkthrough of how it all fits together.

## Why Blazor?

I went with **ASP.NET Core 8** and **Blazor** for a few reasons:

- **Server-side rendering by default** — Pages render on the server and stream to the browser. No heavy JS bundle, fast initial loads, great for SEO.
- **Interactive Server mode where needed** — Admin pages and anything requiring real-time UI (like the blog editor or delete confirmations) use `@rendermode InteractiveServer` over a SignalR connection.
- **C# everywhere** — One language for the backend services, the page logic, and the component model. No context switching.
- **Razor components** — Clean, composable UI with Bootstrap 5.3 and a custom dark theme.

The result is a site that feels like a single-page app but is actually server-rendered HTML with targeted interactivity.

## The Blog Engine

I didn't want a database for blog content. Markdown files are portable, version-controlled, and easy to write. The blog engine works like this:

1. Posts live as `.md` files in `Content/posts/` with YAML front matter
2. `BlogService` reads the directory, parses the front matter with **YamlDotNet**, and converts Markdown to HTML with **Markdig**
3. Posts are cached in-memory for 5 minutes to avoid re-reading the filesystem on every request
4. The admin panel has a built-in editor that writes new `.md` files directly to disk

A typical post file looks like this:

```yaml
---
title: "How I Built This Site"
slug: how-i-built-this-site
date: 2026-02-07
category: Technology
tags:
  - Blazor
  - .NET
draft: false
---

# Your markdown content here...
```

The filename format is `YYYY-MM-DD-slug-name.md`, and the service extracts the date and slug from either the front matter or the filename itself. This means I can create posts by dropping a file into a directory or by using the admin UI — both work.

## Live Cycling Data

The cycling stats on the homepage and `/biking` page pull real data from the **Intervals.icu** REST API. I registered a typed `HttpClient` in DI:

```csharp
builder.Services.AddHttpClient<ICyclingService, IntervalsIcuService>();
```

The service fetches year-to-date stats (distance, elevation, ride count, average speed) and recent activities. If the API is unavailable or unconfigured, it falls back to sample data — the UI shows a green "Live Data Connected" or orange "Using Sample Data" indicator so I always know what I'm looking at.

## Traffic Analytics

Instead of adding a third-party analytics script, I built lightweight traffic tracking with a custom middleware:

```
Request → TrafficTracking Middleware → SQLite (via EF Core) → Admin Dashboard
```

Every page view gets logged with the path, timestamp, IP, user agent, and referer. The admin dashboard shows page views, unique visitors, and average response time for the last 30 days. It's basic, but it's private — no data leaves my server.

## Authentication

The admin section uses **cookie-based authentication** — no external identity providers, no OAuth complexity. A single admin account is configured via environment variables. The login form POSTs to a minimal API endpoint that validates credentials and issues a cookie:

```csharp
builder.Services.AddAuthentication(CookieAuthenticationDefaults.AuthenticationScheme)
    .AddCookie(options =>
    {
        options.LoginPath = "/admin/login";
        options.ExpireTimeSpan = TimeSpan.FromHours(24);
        options.Cookie.HttpOnly = true;
    });
```

Admin pages are protected with `@attribute [Authorize]`. Simple and effective for a single-user site.

## SEO and Feeds

Every page includes **Open Graph** and **Twitter Card** meta tags via Blazor's `<HeadContent>` component. Blog posts get additional structured metadata like `article:published_time` and `article:tag`.

The site also generates:

- **RSS Feed** at `/feed.xml` — standard RSS 2.0 with Atom self-link
- **Sitemap** at `/sitemap.xml` — includes all static pages and dynamically lists blog posts
- **Reading progress bar** on blog posts — a thin gradient bar at the top of the viewport that tracks scroll position

## Deployment

The site runs in a **Docker container** with a multi-stage build:

```dockerfile
FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build
# restore, build, publish...

FROM mcr.microsoft.com/dotnet/aspnet:8.0 AS final
HEALTHCHECK --interval=30s --timeout=3s \
    CMD curl -f http://localhost:5002/health || exit 1
ENTRYPOINT ["dotnet", "PersonalSite.dll"]
```

The health check endpoint at `/health` means my orchestrator knows when the app is ready. The container runs on port 5002 behind a reverse proxy.

## The Design

The UI is a custom **dark theme** built on Bootstrap 5.3's `data-bs-theme="dark"` mode. I added CSS custom properties for a consistent design system:

- Glass-morphism cards (`card-glass`) with backdrop blur and subtle borders
- A gradient accent inspired by cycling power zone colors
- Stat cards with colored icons for the cycling dashboard
- Responsive layouts that work from mobile to ultrawide

No JavaScript framework. No build toolchain. Just CSS custom properties, Bootstrap utilities, and Blazor components.

## What I'd Do Differently

A few things I'm considering for the future:

- **Markdown preview** in the blog editor — right now it's a plain textarea
- **Image uploads** — currently images would need to be manually placed in `wwwroot`
- **Full-text search** — the current client-side filtering works fine for a small number of posts but won't scale forever

## Wrapping Up

The best personal site is one you'll actually maintain. By building on a stack I use every day, updating this site feels like a natural extension of my workflow — not a chore. The entire thing is a single .NET project with no external databases (besides a SQLite file for analytics), no build pipelines for the frontend, and no third-party services beyond Intervals.icu for cycling data.

If you're an SRE or backend engineer thinking about building a personal site, consider using the tools you already know. You don't need a trendy frontend framework — you need something you'll keep shipping.
