# NestUp Work Tracker

A Python Flask application demonstrating a dependency-driven work management system with threshold-based blocking and cascading status updates.

## Folder Structure

```
nestup_work_tracker/
├── app.py                          # Entry point
├── requirements.txt                # Python dependencies
├── README.md                       # This file
└── app/
    ├── __init__.py                 # Flask app factory
    ├── models.py                   # SQLAlchemy database models
    ├── logic.py                    # Core business logic
    ├── routes.py                   # All endpoints and handlers
    ├── seed.py                     # Demo data initialization
    └── templates/
        ├── base.html               # Base template with styling
        ├── login.html              # Login form + demo credentials
        ├── admin.html              # Admin dashboard
        └── member.html             # Member dashboard
```

## Quick Start

### Prerequisites
- Python 3.8+ installed on your system

### Setup Instructions

#### Windows PowerShell
```powershell
# Navigate to project directory
cd nestup_work_tracker

# Create virtual environment
python -m venv venv

# Activate virtual environment
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the app
python app.py
```

#### macOS/Linux
```bash
# Navigate to project directory
cd nestup_work_tracker

# Create virtual environment
python -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the app
python app.py
```

### Access the Application

After running `python app.py`, open your browser and navigate to:
```
http://127.0.0.1:5000
```

## Demo Accounts

The application seeds demo data automatically on first run:

| Name | Email | Password | Role |
|------|-------|----------|------|
| Admin User | admin@nestup.local | admin123 | admin |
| Aisha | aisha@nestup.local | member123 | member |
| Rahul | rahul@nestup.local | member123 | member |

### Usage Examples

**Admin Dashboard** (Login as admin@nestup.local / admin123)
- Create new members and assign skills
- Create work items and assign to members
- Create dependencies between work items
- View workload distribution and bottlenecks
- Monitor all work items and their status

**Member Dashboard** (Login as any member account)
- View assigned work items
- Update progress on tasks
- Mark tasks as blocked with reasons
- See downstream impact of your work (which tasks depend on yours)

## Architecture Overview

### Database Models

**User**
- id, name, email, password, role (admin/member)
- Relationships: skills (many-to-many), work_items (one-to-many)

**Skill**
- id, name
- Relationships: users (many-to-many), work_items (many-to-many)

**WorkItem**
- id, title, description, priority, progress (0-100%), status, blocked_reason
- Relationships: assignee (User), skills (many-to-many), upstream_dependencies, downstream_dependencies

**Dependency**
- id, predecessor_id, successor_id, dep_type (full/partial), threshold (0-100)
- Rules:
  - Full dependency: predecessor must reach 100% AND status=done
  - Partial dependency: predecessor must reach the threshold %
  - Threshold 0 is explicitly rejected (prevents immediate unblocking)

### Core Business Logic (app/logic.py)

#### 1. `validate_threshold(dep_type, threshold)` 
Validates dependency rule:
- Full dependencies must have threshold=100
- Partial dependencies must have threshold between 1-99
- Threshold 0 is rejected

#### 2. `would_create_cycle(predecessor_id, successor_id, all_dependencies)`
Uses BFS to detect circular dependencies before creation:
- Builds adjacency graph from existing dependencies
- Adds new edge and checks if predecessor is reachable from successor
- Prevents creation if cycle is detected

#### 3. `dependency_satisfied(dep)`
Checks if a dependency is met:
- Full: predecessor.progress >= 100 AND predecessor.status == 'done'
- Partial: predecessor.progress >= threshold

#### 4. `recalculate_work_item_status(work_item)`
Updates work item status based on dependencies:
- If any upstream dependency is unmet: status = 'blocked', blocked_reason = list of unmet dependencies
- If all dependencies met:
  - progress == 0: status = 'in-progress'
  - 0 < progress < 100: status = 'in-progress'
  - progress == 100: status = 'done'
  - blocked_reason = None

#### 5. `cascade_status_updates(db, changed_item_id)`
Propagates status changes downstream:
- Uses BFS traversal of dependency graph
- For each downstream work item, recalculates status
- Only queues items where status actually changed (avoids cycles)
- Ensures all transitive effects are captured

### Routes (app/routes.py)

**Public Routes**
- GET/POST `/login` - Authentication
- GET `/logout` - Clear session

**Authenticated Routes**
- GET `/dashboard` - Redirects to admin or member dashboard based on role
- GET/POST `/admin` - Admin dashboard (create members, work items, dependencies; view analytics)
- GET/POST `/member` - Member dashboard (view assigned work, update progress, mark blocked)

### Request Flow Example

1. Admin creates dependency: w1 → w2 (partial, 50%)
2. w2 status recalculated: if w1.progress < 50%, w2 becomes blocked
3. Member updates w1 progress from 30% → 60%
4. POST to /member with action=update_progress, progress=60
5. w1.progress updated, cascade_status_updates(db, w1.id) called
6. BFS traverses: w1 → w2
7. w2 recalculated: w1.progress (60%) >= threshold (50%), so w2 unblocks
8. If w2 blocks other items, they are also recalculated transitively

### Data Persistence

- Database: SQLite (nestup.db, auto-created)
- Passwords: Plaintext (demo only, not production-ready)
- Secret key: hardcoded to 'nestup-demo-secret'

## Algorithm Explanation

### Status Recalculation Algorithm

The core algorithm is `recalculate_work_item_status()`:

```
1. If work_item.status is already 'done', return (no changes to done items)
2. Find all unmet upstream dependencies:
   - For each upstream dependency:
     - Check if predecessor.progress >= threshold (or full condition)
     - If not satisfied, add to unmet list
3. If unmet dependencies exist:
   - Set status = 'blocked'
   - Set blocked_reason = "Waiting on: [list of unmet]"
4. Else (all dependencies satisfied):
   - If progress == 0: status = 'in-progress'
   - Elif progress < 100: status = 'in-progress'
   - Else (progress == 100): status = 'done'
   - Set blocked_reason = None
```

### Cascading Updates Algorithm

The `cascade_status_updates()` function uses BFS to propagate changes:

```
1. Initialize: queue = [changed_item_id], visited = empty set
2. While queue not empty:
   a. Dequeue current_id
   b. If already visited, skip
   c. Mark as visited
   d. For each downstream dependency of current:
      - Get successor work item
      - Capture before state (status, blocked_reason)
      - Call recalculate_work_item_status(successor)
      - Capture after state
      - If state changed, enqueue successor.id
3. Flush all changes to database
```

This ensures transitive effects propagate correctly without infinite loops.

## Testing the Dependency Chain

The seeded data includes a sample chain:
- w1 (Set up database schema) → 100% done ✓
- w2 (Build admin dashboard) → 60% in-progress (depends on w1 full)
- w3 (Member progress screen) → 0% blocked (depends on w2 partial 50%)
- w4 (Dependency engine tests) → 0% blocked (depends on w3 full)

**To test the flow:**
1. Login as Aisha (aisha@nestup.local / member123)
2. Set w1 to 100% (already done, but you can re-confirm)
3. Observe w2 remains in-progress (already met the full dependency)
4. Login as Rahul (rahul@nestup.local / member123)
5. Advance w2 progress to 60% or higher
6. Observe w3 unblocks to 'in-progress'
7. Continue advancing w3 to 100%
8. Observe w4 unblocks

## Key Design Decisions

- **SQLite**: Simple, file-based, no server setup
- **Plaintext passwords**: Demo-only, not secure
- **BFS cycle detection**: O(V+E) prevention of circular dependencies
- **Cascade with change tracking**: Avoids redundant recalculations
- **Threshold validation**: 0 is rejected to maintain blocking semantics
- **Inline CSS**: Single HTTP request, no stylesheet dependencies

## Future Improvements

- Password hashing (werkzeug.security)
- Edit/delete actions for work items and dependencies
- User role granularity (read-only members, limited admins)
- Dependency graph visualization
- Export/report functionality
- Audit logging of status transitions
- Notification system for blocked items

## Notes

- Database is recreated fresh on each server restart (reset by deleting nestup.db, then restart app.py)
- No transaction rollback on dependency validation errors (form is re-submitted)
- Large dependency graphs may experience performance issues (optimize queries with indexes)
