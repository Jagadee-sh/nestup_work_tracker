from collections import defaultdict, deque
from .models import WorkItem, Dependency


def validate_threshold(dep_type, threshold):
    if dep_type == 'full' and threshold != 100:
        return False, 'Full dependency threshold must be exactly 100.'
    if dep_type == 'partial' and (threshold <= 0 or threshold >= 100):
        return False, 'Partial dependency threshold must be between 1 and 99. Threshold 0 would unblock immediately and break blocking logic.'
    return True, ''


def would_create_cycle(predecessor_id, successor_id, all_dependencies):
    graph = defaultdict(list)
    for dep in all_dependencies:
        graph[dep.predecessor_id].append(dep.successor_id)
    graph[predecessor_id].append(successor_id)

    queue = deque([successor_id])
    seen = set()
    while queue:
        node = queue.popleft()
        if node == predecessor_id:
            return True
        if node in seen:
            continue
        seen.add(node)
        for nxt in graph[node]:
            queue.append(nxt)
    return False


def dependency_satisfied(dep):
    if dep.dep_type == 'full':
        return dep.predecessor.progress >= 100 and dep.predecessor.status == 'done'
    return dep.predecessor.progress >= dep.threshold


def recalculate_work_item_status(work_item):
    if work_item.status == 'done':
        return
    unmet = [dep for dep in work_item.upstream_dependencies if not dependency_satisfied(dep)]
    if unmet:
        work_item.status = 'blocked'
        pieces = []
        for dep in unmet:
            rule = f"{dep.predecessor.title} ({dep.dep_type}:{dep.threshold}%)"
            pieces.append(rule)
        work_item.blocked_reason = 'Waiting on: ' + ', '.join(pieces)
    else:
        if work_item.progress == 0:
            work_item.status = 'in-progress'
        elif work_item.progress < 100:
            work_item.status = 'in-progress'
        else:
            work_item.status = 'done'
        work_item.blocked_reason = None


def cascade_status_updates(db, changed_item_id):
    visited = set()
    queue = deque([changed_item_id])

    while queue:
        current_id = queue.popleft()
        if current_id in visited:
            continue
        visited.add(current_id)

        current = WorkItem.query.get(current_id)
        for dep in current.downstream_dependencies:
            successor = dep.successor
            before = (successor.status, successor.blocked_reason)
            recalculate_work_item_status(successor)
            after = (successor.status, successor.blocked_reason)
            if before != after:
                queue.append(successor.id)

    db.session.flush()
