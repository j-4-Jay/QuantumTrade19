from __future__ import annotations
from collections import defaultdict
from typing import Callable
import threading, uuid

class EventBus:
    def __init__(self):
        self._subs = defaultdict(list); self._lock = threading.Lock()
    def subscribe(self, topic, handler):
        with self._lock: self._subs[topic].append(handler)
    def unsubscribe(self, topic, handler):
        with self._lock:
            if handler in self._subs.get(topic, []): self._subs[topic].remove(handler)
    def publish(self, topic, payload=None):
        event_id = str(uuid.uuid4()); data = {"event_id": event_id, "topic": topic, **(payload or {})}
        for h in list(self._subs.get(topic, [])): h(data)
        return event_id

event_bus = EventBus()
