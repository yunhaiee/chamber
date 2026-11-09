"""One local queue. All LFM3 calls run on one worker thread, chat first, the automatic day after."""
import itertools
import queue
import threading
from concurrent.futures import Future

CHAT = 0
DAY = 1

_jobs = queue.PriorityQueue()
_seq = itertools.count()
_started = False
_open = 0
_lock = threading.Lock()


def _worker():
    while True:
        _, _, fn, future = _jobs.get()
        try:
            future.set_result(fn())
        except Exception as e:  # handed to the waiting thread
            future.set_exception(e)


def _ensure():
    global _started
    with _lock:
        if not _started:
            threading.Thread(target=_worker, daemon=True, name="local-queue").start()
            _started = True


def run(fn, priority=CHAT):
    """Run fn on the local worker and wait for its result."""
    global _open
    _ensure()
    future = Future()
    with _lock:
        _open += 1
    _jobs.put((priority, next(_seq), fn, future))
    try:
        return future.result()
    finally:
        with _lock:
            _open -= 1


def busy():
    """True while any local call is queued or running."""
    with _lock:
        return _open > 0
