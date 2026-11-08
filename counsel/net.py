"""Real socket check to the cloud host every 2 seconds. Public work waits while it fails."""
import threading
import time

from . import llm

_online = None
_started = False
_callbacks = []


def online():
    return bool(_online)


def on_reconnect(fn):
    _callbacks.append(fn)


def _loop():
    global _online
    while True:
        now_online = llm.cloud_online()
        came_back = now_online and _online is False
        _online = now_online
        if came_back:
            for fn in _callbacks:
                threading.Thread(target=fn, daemon=True).start()
        time.sleep(2)


def start():
    global _started, _online
    if not _started:
        _started = True
        _online = llm.cloud_online()
        threading.Thread(target=_loop, daemon=True, name="net-check").start()
