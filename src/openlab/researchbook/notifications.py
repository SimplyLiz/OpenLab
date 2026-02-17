"""In-process notification system for thread watchers."""

from __future__ import annotations

from sqlalchemy.orm import Session

from openlab.researchbook.models import NotifyOn, ThreadWatcher


def notify_watchers(db: Session, thread_id: int, event_type: str, data: dict) -> int:
    """Notify all watchers of a thread about an event.

    Returns the number of notifications dispatched.
    For Phase 2, notifications are stored in-memory.
    """
    watchers = (
        db.query(ThreadWatcher)
        .filter(ThreadWatcher.thread_id == thread_id)
        .all()
    )

    count = 0
    for watcher in watchers:
        if _should_notify(watcher.notify_on, event_type):
            _notifications.append({
                "watcher_name": watcher.watcher_name,
                "thread_id": thread_id,
                "event_type": event_type,
                "data": data,
            })
            count += 1

    return count


def get_notifications(db: Session, watcher_name: str) -> list[dict]:
    """Get pending notifications for a watcher."""
    pending = [n for n in _notifications if n["watcher_name"] == watcher_name]
    # Clear returned notifications
    for n in pending:
        _notifications.remove(n)
    return pending


def _should_notify(notify_on: str, event_type: str) -> bool:
    if notify_on == NotifyOn.ALL.value:
        return True
    if notify_on == NotifyOn.CHALLENGES.value and event_type == "challenge":
        return True
    return notify_on == NotifyOn.CORRECTIONS.value and event_type == "correction"


# In-process notification store
_notifications: list[dict] = []
