from threading import Event, Lock, Thread
from typing import Any, Callable, override

_thread_pool: dict[str, 'ManagedThread'] = {}
_thread_pool_lock: Lock = Lock()


class ManagedThread(Thread):
    '''A thread that can be managed and stopped gracefully.
       Uses a thread pool to keep track of active threads by name.
       Use the `should_stop` property to check if the thread should stop in loops, or else `stop`
       will block until the thread finishes execution, which may not be desired in all cases.
    '''
    name: str
    args: tuple[Any, ...]
    kwargs: dict[str, Any] | None
    _stop_event: Event
    _target: Callable[..., object] | None

    @override
    def __init__(self,
                 name: str,
                 group: None = None,
                 target: Callable[..., object] | None = None,
                 args: tuple[Any, ...] = (),
                 kwargs: dict[str, Any] | None = None):
        super().__init__(group, target, name, args, kwargs)
        self.name = name
        self._target = target
        self.args = args
        self.kwargs = kwargs
        self._stop_event = Event()

    @override
    def run(self):
        try:
            with _thread_pool_lock:
                _thread_pool[self.name] = self
            if self._target:
                _ = self._target(self, *self.args, **self.kwargs if self.kwargs else {})
            else:
                super().run()
        finally:
            with _thread_pool_lock:
                _ = _thread_pool.pop(self.name, None)

    def stop(self):
        self._stop_event.set()
        if self.is_alive():
            self.join()

    @property
    def should_stop(self) -> bool:
        return self._stop_event.is_set()

    @classmethod
    def get(cls, name: str) -> 'ManagedThread | None':
        with _thread_pool_lock:
            return _thread_pool.get(name)

