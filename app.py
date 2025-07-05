from flask import Flask, render_template, jsonify, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
import json
import os
from datetime import datetime, timedelta
from blog_manager import BlogManager
from forms import LoginForm, BlogPostForm
from user import User

# Import traffic tracking components
from models import db
from traffic_tracker import TrafficTracker
from sqlalchemy import func, desc

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key-change-in-production')

# SQLite Configuration for traffic tracking
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(basedir, "traffic_analytics.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db.init_app(app)
tracker = TrafficTracker(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'admin_login'
login_manager.login_message = 'Please log in to access the admin panel.'

# Initialize Blog Manager
blog_manager = BlogManager()


@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)


# Initialize Strava service (with error handling)
try:
    from strava_service import StravaService

    strava = StravaService()
    STRAVA_ENABLED = True
except Exception as e:
    print(f"Strava service not available: {e}")
    strava = None
    STRAVA_ENABLED = False


# Load blog posts from BlogManager
def load_blog_posts():
    return blog_manager.load_posts()


@app.route('/')
def index():
    posts = load_blog_posts()
    recent_posts = sorted(posts, key=lambda x: x['date'], reverse=True)[:3]
    return render_template('index.html', recent_posts=recent_posts)


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/hardware')
def hardware():
    return render_template('hardware.html')


@app.route('/biking')
def biking():
    ytd_stats = None
    recent_activities = []

    if STRAVA_ENABLED and strava:
        try:
            ytd_stats = strava.get_ytd_stats()
            recent_activities = strava.format_recent_activities()
        except Exception as e:
            print(f"Error fetching Strava data: {e}")
            ytd_stats = {
                'distance': 0,
                'count': 0,
                'elevation': 0,
                'time': 0
            }
    else:
        ytd_stats = {
            'distance': 2450,
            'count': 127,
            'elevation': 45600,
            'time': 156
        }
        recent_activities = [
            {
                'name': 'Morning Training Ride',
                'distance': 25.3,
                'elevation': 1200,
                'time': '1h 45m',
                'date': 'January 5, 2025'
            }
        ]

    current_time = datetime.now().strftime('%B %d, %Y at %I:%M %p')

    return render_template('biking.html',
                           ytd_stats=ytd_stats,
                           recent_activities=recent_activities,
                           strava_enabled=STRAVA_ENABLED,
                           last_updated=current_time)


@app.route('/blog')
def blog():
    posts = load_blog_posts()
    posts = sorted(posts, key=lambda x: x['date'], reverse=True)
    return render_template('blog.html', posts=posts)


@app.route('/blog/<int:post_id>')
def blog_post(post_id):
    post = blog_manager.get_post(post_id)
    if not post:
        return "Post not found", 404
    return render_template('blog_post.html', post=post)


# Admin Routes
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if current_user.is_authenticated:
        return redirect(url_for('admin_dashboard'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.authenticate(form.username.data, form.password.data)
        if user:
            login_user(user)
            flash('Logged in successfully!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid username or password.', 'error')

    return render_template('admin/login.html', form=form)


@app.route('/admin/logout')
@login_required
def admin_logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))


@app.route('/admin')
@login_required
def admin_dashboard():
    posts = load_blog_posts()
    posts = sorted(posts, key=lambda x: x['date'], reverse=True)
    return render_template('admin/dashboard.html', posts=posts)


@app.route('/admin/post/new', methods=['GET', 'POST'])
@login_required
def admin_new_post():
    form = BlogPostForm()
    if form.validate_on_submit():
        blog_manager.create_post(
            title=form.title.data,
            content=form.content.data,
            category=form.category.data,
            excerpt=form.excerpt.data or None
        )
        flash('Post created successfully!', 'success')
        return redirect(url_for('admin_dashboard'))

    return render_template('admin/edit_post.html', form=form, title='New Post')


@app.route('/admin/post/<int:post_id>/edit', methods=['GET', 'POST'])
@login_required
def admin_edit_post(post_id):
    post = blog_manager.get_post(post_id)
    if not post:
        flash('Post not found.', 'error')
        return redirect(url_for('admin_dashboard'))

    form = BlogPostForm(obj=post)
    if form.validate_on_submit():
        blog_manager.update_post(
            post_id=post_id,
            title=form.title.data,
            content=form.content.data,
            category=form.category.data,
            excerpt=form.excerpt.data or None
        )
        flash('Post updated successfully!', 'success')
        return redirect(url_for('admin_dashboard'))

    return render_template('admin/edit_post.html', form=form, post=post, title='Edit Post')


@app.route('/admin/post/<int:post_id>/delete', methods=['POST'])
@login_required
def admin_delete_post(post_id):
    blog_manager.delete_post(post_id)
    flash('Post deleted successfully!', 'success')
    return redirect(url_for('admin_dashboard'))


# Traffic Analytics Admin Route
@app.route('/admin/traffic')
@login_required
def admin_traffic():
    from models import PageView, UniqueVisitor

    # Get date range from query params (default to last 30 days)
    days = int(request.args.get('days', 30))
    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=days)

    # Basic stats
    total_views = PageView.query.filter(
        func.date(PageView.timestamp).between(start_date, end_date)
    ).count()

    unique_visitors = db.session.query(func.count(func.distinct(PageView.ip_address))).filter(
        func.date(PageView.timestamp).between(start_date, end_date)
    ).scalar()

    avg_response_time = db.session.query(func.avg(PageView.response_time)).filter(
        func.date(PageView.timestamp).between(start_date, end_date)
    ).scalar() or 0

    # Calculate bounce rate (sessions with only one page view)
    single_page_sessions = db.session.query(
        PageView.session_id
    ).filter(
        func.date(PageView.timestamp).between(start_date, end_date)
    ).group_by(PageView.session_id).having(func.count(PageView.id) == 1).count()

    total_sessions = db.session.query(
        func.count(func.distinct(PageView.session_id))
    ).filter(
        func.date(PageView.timestamp).between(start_date, end_date)
    ).scalar()

    bounce_rate = (single_page_sessions / total_sessions * 100) if total_sessions > 0 else 0

    # Top pages
    top_pages = db.session.query(
        PageView.path,
        func.count(PageView.id).label('views')
    ).filter(
        func.date(PageView.timestamp).between(start_date, end_date)
    ).group_by(PageView.path).order_by(desc('views')).limit(10).all()

    # Top referrers
    top_referrers = db.session.query(
        PageView.referrer,
        func.count(PageView.id).label('views')
    ).filter(
        func.date(PageView.timestamp).between(start_date, end_date),
        PageView.referrer.isnot(None),
        PageView.referrer != ''
    ).group_by(PageView.referrer).order_by(desc('views')).limit(10).all()

    # Daily views for chart - Fixed to handle SQLite date strings
    daily_views_raw = db.session.query(
        func.date(PageView.timestamp).label('date'),
        func.count(PageView.id).label('views'),
        func.count(func.distinct(PageView.ip_address)).label('unique_visitors')
    ).filter(
        func.date(PageView.timestamp).between(start_date, end_date)
    ).group_by(func.date(PageView.timestamp)).order_by('date').all()

    # Recent activity (last 50 page views)
    recent_activity = PageView.query.filter(
        PageView.timestamp >= datetime.utcnow() - timedelta(hours=24)
    ).order_by(desc(PageView.timestamp)).limit(50).all()

    stats = {
        'total_views': total_views,
        'unique_visitors': unique_visitors,
        'avg_response_time': round(avg_response_time, 2),
        'bounce_rate': round(bounce_rate, 2)
    }

    # Format daily views for JSON - Handle both string and date objects
    daily_views_json = []
    for day in daily_views_raw:
        # Handle case where SQLite returns date as string
        if isinstance(day.date, str):
            date_str = day.date
        else:
            date_str = day.date.isoformat()

        daily_views_json.append({
            'date': date_str,
            'views': day.views,
            'unique_visitors': day.unique_visitors
        })

    return render_template('admin/traffic.html',
                           stats=stats,
                           top_pages=top_pages,
                           top_referrers=top_referrers,
                           daily_views=daily_views_json,
                           recent_activity=recent_activity,
                           days=days)

# Real-time traffic API for admin dashboard
@app.route('/admin/traffic/api/realtime')
@login_required
def realtime_traffic():
    from models import PageView

    # Last 5 minutes of traffic
    five_min_ago = datetime.utcnow() - timedelta(minutes=5)

    recent_views = PageView.query.filter(
        PageView.timestamp >= five_min_ago
    ).order_by(desc(PageView.timestamp)).limit(50).all()

    active_users = db.session.query(func.count(func.distinct(PageView.session_id))).filter(
        PageView.timestamp >= five_min_ago
    ).scalar()

    return jsonify({
        'active_users': active_users,
        'recent_views': [{
            'path': view.path,
            'timestamp': view.timestamp.isoformat(),
            'ip_address': view.ip_address[:8] + '...',  # Partial IP for privacy
            'country': view.country,
            'city': view.city
        } for view in recent_views]
    })


@app.route('/api/strava-stats')
def strava_stats_api():
    if not STRAVA_ENABLED or not strava:
        return jsonify({
            'error': 'Strava service not available',
            'ytd_stats': None,
            'recent_activities': []
        }), 503

    try:
        ytd_stats = strava.get_ytd_stats()
        recent_activities = strava.format_recent_activities()

        return jsonify({
            'ytd_stats': ytd_stats,
            'recent_activities': recent_activities
        })
    except Exception as e:
        return jsonify({
            'error': str(e),
            'ytd_stats': None,
            'recent_activities': []
        }), 500


@app.route('/health')
def health_check():
    return {'status': 'healthy', 'timestamp': datetime.utcnow().isoformat()}


# Create database tables on startup
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)