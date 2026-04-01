from .models import db, User, Skill, WorkItem, Dependency
from .logic import recalculate_work_item_status


def ensure_seed_data():
    if User.query.first():
        return

    skills = {name: Skill(name=name) for name in ['Python', 'Flask', 'SQL', 'UI', 'Testing']}
    db.session.add_all(skills.values())
    db.session.flush()

    admin = User(name='Admin User', email='admin@nestup.local', password='admin123', role='admin', skills=[skills['Python'], skills['SQL']])
    aisha = User(name='Aisha', email='aisha@nestup.local', password='member123', role='member', skills=[skills['Python'], skills['Flask']])
    rahul = User(name='Rahul', email='rahul@nestup.local', password='member123', role='member', skills=[skills['UI'], skills['Testing']])
    db.session.add_all([admin, aisha, rahul])
    db.session.flush()

    w1 = WorkItem(title='Set up database schema', description='Create tables for users, work items, and dependencies.', priority='high', progress=100, status='done', assignee_id=aisha.id, skills=[skills['Python'], skills['SQL']])
    w2 = WorkItem(title='Build admin dashboard', description='Create admin dashboard with metrics and overview.', priority='critical', progress=60, status='in-progress', assignee_id=rahul.id, skills=[skills['UI'], skills['Flask']])
    w3 = WorkItem(title='Member progress screen', description='Build member panel with progress update actions.', priority='high', progress=0, status='blocked', assignee_id=rahul.id, skills=[skills['UI']])
    w4 = WorkItem(title='Dependency engine tests', description='Validate blocking and unblocking behavior.', priority='medium', progress=0, status='blocked', assignee_id=aisha.id, skills=[skills['Testing'], skills['Python']])
    db.session.add_all([w1, w2, w3, w4])
    db.session.flush()

    d1 = Dependency(predecessor_id=w1.id, successor_id=w2.id, dep_type='full', threshold=100)
    d2 = Dependency(predecessor_id=w2.id, successor_id=w3.id, dep_type='partial', threshold=50)
    d3 = Dependency(predecessor_id=w3.id, successor_id=w4.id, dep_type='full', threshold=100)
    db.session.add_all([d1, d2, d3])
    db.session.flush()

    for item in WorkItem.query.all():
        recalculate_work_item_status(item)
    db.session.commit()
