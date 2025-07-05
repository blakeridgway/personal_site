from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

db = SQLAlchemy()


class PageView(db.Model):
    __tablename__ = 'page_views'

    id = db.Column(db.Integer, primary_key=True)
    ip_address = db.Column(db.String(45), index=True)
    user_agent = db.Column(db.Text)
    path = db.Column(db.String(255), index=True)
    method = db.Column(db.String(10))
    referrer = db.Column(db.String(500))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    response_time = db.Column(db.Float)
    status_code = db.Column(db.Integer, index=True)
    country = db.Column(db.String(2), index=True)
    city = db.Column(db.String(100))
    session_id = db.Column(db.String(255), index=True)


class UniqueVisitor(db.Model):
    __tablename__ = 'unique_visitors'

    id = db.Column(db.Integer, primary_key=True)
    ip_address = db.Column(db.String(45), index=True)
    user_agent_hash = db.Column(db.String(64), index=True)
    first_visit = db.Column(db.DateTime, default=datetime.utcnow)
    last_visit = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    visit_count = db.Column(db.Integer, default=1)
    country = db.Column(db.String(2))
    city = db.Column(db.String(100))

    __table_args__ = (
        db.Index('idx_visitor_lookup', 'ip_address', 'user_agent_hash'),
    )