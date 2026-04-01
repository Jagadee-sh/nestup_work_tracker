from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from .models import db, User, Skill, WorkItem, Dependency
from .logic import validate_threshold, would_create_cycle, recalculate_work_item_status, cascade_status_updates

main = Blueprint('main', __name__)


def current_user():
    uid = session.get('user_id')
    return User.query.get(uid) if uid else None


def login_required(role=None):
    def decorator(fn):
        from functools import wraps
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user = current_user()
            if not user:
                return redirect(url_for('main.login'))
            if role and user.role != role:
                flash('Access denied for this view.', 'error')
                return redirect(url_for('main.dashboard'))
            return fn(*args, **kwargs)
        return wrapper
    return decorator


@main.route('/')
def home():
    return redirect(url_for('main.login'))


@main.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email, password=password).first()
        if user:
            session['user_id'] = user.id
            return redirect(url_for('main.dashboard'))
        flash('Invalid credentials.', 'error')
    demo_users = User.query.all()
    return render_template('login.html', demo_users=demo_users)


@main.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('main.login'))


@main.route('/dashboard')
@login_required()
def dashboard():
    user = current_user()
    return redirect(url_for('main.admin_dashboard' if user.role == 'admin' else 'main.member_dashboard'))


@main.route('/admin', methods=['GET', 'POST'])
@login_required(role='admin')
def admin_dashboard():
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'create_member':
            name = request.form['name']
            email = request.form['email']
            password = request.form['password']
            skill_names = request.form.getlist('skills')
            member = User(name=name, email=email, password=password, role='member')
            member.skills = Skill.query.filter(Skill.name.in_(skill_names)).all() if skill_names else []
            db.session.add(member)
            db.session.commit()
            flash('Member created successfully.', 'success')

        elif action == 'create_work_item':
            item = WorkItem(
                title=request.form['title'],
                description=request.form['description'],
                priority=request.form['priority'],
                assignee_id=int(request.form['assignee_id']),
                progress=0,
                status='blocked'
            )
            skill_names = request.form.getlist('skills')
            item.skills = Skill.query.filter(Skill.name.in_(skill_names)).all() if skill_names else []
            db.session.add(item)
            db.session.flush()
            recalculate_work_item_status(item)
            db.session.commit()
            flash('Work item created successfully.', 'success')

        elif action == 'create_dependency':
            predecessor_id = int(request.form['predecessor_id'])
            successor_id = int(request.form['successor_id'])
            dep_type = request.form['dep_type']
            threshold = int(request.form['threshold'])

            if predecessor_id == successor_id:
                flash('A work item cannot depend on itself.', 'error')
            else:
                ok, msg = validate_threshold(dep_type, threshold)
                if not ok:
                    flash(msg, 'error')
                elif would_create_cycle(predecessor_id, successor_id, Dependency.query.all()):
                    flash('Circular dependency detected. This dependency was rejected.', 'error')
                else:
                    dep = Dependency(predecessor_id=predecessor_id, successor_id=successor_id, dep_type=dep_type, threshold=threshold)
                    db.session.add(dep)
                    db.session.flush()
                    successor = WorkItem.query.get(successor_id)
                    recalculate_work_item_status(successor)
                    db.session.commit()
                    flash('Dependency created successfully.', 'success')
        return redirect(url_for('main.admin_dashboard'))

    work_items = WorkItem.query.order_by(WorkItem.created_at.desc()).all()
    members = User.query.filter_by(role='member').all()
    skills = Skill.query.order_by(Skill.name).all()
    dependencies = Dependency.query.all()

    workload = []
    for member in members:
        total = len(member.work_items)
        critical = len([w for w in member.work_items if w.priority == 'critical'])
        overloaded = total >= 4 or critical >= 2
        match_score = sum(1 for w in member.work_items if set(s.name for s in w.skills).intersection({s.name for s in member.skills}))
        workload.append({'member': member, 'total': total, 'critical': critical, 'overloaded': overloaded, 'match_score': match_score})

    bottlenecks = [w for w in work_items if any(dep.successor.status == 'blocked' for dep in w.downstream_dependencies)]
    return render_template('admin.html', user=current_user(), work_items=work_items, members=members, skills=skills, dependencies=dependencies, workload=workload, bottlenecks=bottlenecks)


@main.route('/member', methods=['GET', 'POST'])
@login_required(role='member')
def member_dashboard():
    user = current_user()
    if request.method == 'POST':
        item = WorkItem.query.get_or_404(int(request.form['work_item_id']))
        if item.assignee_id != user.id:
            flash('You can update only your assigned work.', 'error')
            return redirect(url_for('main.member_dashboard'))

        action = request.form['action']
        if action == 'update_progress':
            progress = max(0, min(100, int(request.form['progress'])))
            item.progress = progress
            if progress == 100:
                item.status = 'done'
                item.blocked_reason = None
            else:
                recalculate_work_item_status(item)
            db.session.flush()
            cascade_status_updates(db, item.id)
            db.session.commit()
            flash('Progress updated and downstream items recalculated.', 'success')

        elif action == 'mark_blocked':
            item.status = 'blocked'
            item.blocked_reason = request.form['blocked_reason']
            db.session.commit()
            flash('Item marked as blocked.', 'success')

        return redirect(url_for('main.member_dashboard'))

    assigned = WorkItem.query.filter_by(assignee_id=user.id).order_by(WorkItem.priority.desc()).all()
    blockers = [item for item in assigned if item.downstream_dependencies]
    return render_template('member.html', user=user, assigned=assigned, blockers=blockers)
