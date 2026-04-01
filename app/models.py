from flask_sqlalchemy import SQLAlchemy
from datetime import datetime


db = SQLAlchemy()

user_skills = db.Table(
    'user_skills',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('skill_id', db.Integer, db.ForeignKey('skill.id'), primary_key=True),
)

work_item_skills = db.Table(
    'work_item_skills',
    db.Column('work_item_id', db.Integer, db.ForeignKey('work_item.id'), primary_key=True),
    db.Column('skill_id', db.Integer, db.ForeignKey('skill.id'), primary_key=True),
)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    skills = db.relationship('Skill', secondary=user_skills, backref='users')
    work_items = db.relationship('WorkItem', backref='assignee', lazy=True)


class Skill(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)


class WorkItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    priority = db.Column(db.String(20), nullable=False)
    progress = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default='blocked')
    blocked_reason = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    assignee_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    skills = db.relationship('Skill', secondary=work_item_skills, backref='work_items')


class Dependency(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    predecessor_id = db.Column(db.Integer, db.ForeignKey('work_item.id'), nullable=False)
    successor_id = db.Column(db.Integer, db.ForeignKey('work_item.id'), nullable=False)
    dep_type = db.Column(db.String(20), nullable=False)
    threshold = db.Column(db.Integer, nullable=False)

    predecessor = db.relationship('WorkItem', foreign_keys=[predecessor_id], backref='downstream_dependencies')
    successor = db.relationship('WorkItem', foreign_keys=[successor_id], backref='upstream_dependencies')
