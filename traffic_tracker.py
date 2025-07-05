from flask import request, g, session
from datetime import datetime
import time
import hashlib
from models import db, PageView, UniqueVisitor


class TrafficTracker:
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        app.before_request(self.before_request)
        app.after_request(self.after_request)

    def before_request(self):
        g.start_time = time.time()

        if 'session_id' not in session:
            session['session_id'] = hashlib.md5(
                f"{request.remote_addr}{time.time()}".encode()
            ).hexdigest()

    def after_request(self, response):
        # Skip tracking for static files
        if (request.endpoint and 'static' in request.endpoint):
            return response

        try:
            self.track_page_view(response)
            self.update_unique_visitor()
        except Exception as e:
            print(f"Traffic tracking error: {e}")

        return response

    def track_page_view(self, response):
        response_time = (time.time() - g.start_time) * 1000

        page_view = PageView(
            ip_address=self.get_real_ip(),
            user_agent=request.headers.get('User-Agent', ''),
            path=request.path,
            method=request.method,
            referrer=request.headers.get('Referer', ''),
            response_time=response_time,
            status_code=response.status_code,
            session_id=session.get('session_id')
        )

        db.session.add(page_view)
        db.session.commit()

    def update_unique_visitor(self):
        ip = self.get_real_ip()
        user_agent = request.headers.get('User-Agent', '')
        user_agent_hash = hashlib.sha256(user_agent.encode()).hexdigest()

        visitor = UniqueVisitor.query.filter_by(
            ip_address=ip,
            user_agent_hash=user_agent_hash
        ).first()

        if visitor:
            visitor.last_visit = datetime.utcnow()
            visitor.visit_count += 1
        else:
            visitor = UniqueVisitor(
                ip_address=ip,
                user_agent_hash=user_agent_hash
            )
            db.session.add(visitor)

        db.session.commit()

    def get_real_ip(self):
        if request.headers.get('X-Forwarded-For'):
            return request.headers.get('X-Forwarded-For').split(',')[0].strip()
        elif request.headers.get('X-Real-IP'):
            return request.headers.get('X-Real-IP')
        return request.remote_addr