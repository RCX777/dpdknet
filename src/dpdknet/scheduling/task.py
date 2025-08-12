import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import override

@dataclass
class TaskResult:
    stdout: str = ''
    stderr: str = ''
    returncode: int = 0

class Task(ABC):
    name: str
    deps: list['Task']
    result: TaskResult

    _done: asyncio.Event

    def __init__(self, name: str, deps: list['Task'] | None = None):
        self.name = name
        self.deps = deps or []
        self._done = asyncio.Event()

    async def run(self):
        if self._done.is_set():
            return

        _ = await asyncio.gather(*(dep._done.wait() for dep in self.deps))
        await self._run()
        self._done.set()

    @abstractmethod
    async def _run(self): ...


class CmdTask(Task):
    result: TaskResult
    cmd: str
    container: str

    def __init__(self,
                 name: str,
                 cmd: str,
                 container: str = '',
                 deps: list['Task'] | None = None):
        super().__init__(name, deps)
        self.cmd = cmd
        self.container = container

    @override
    async def _run(self):
        process = await asyncio.create_subprocess_shell(
            f'docker exec -it dn.{self.container} bash -c "{self.cmd}"'
                if self.container else self.cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        self.result = TaskResult(
            stdout=stdout.decode().strip(),
            stderr=stderr.decode().strip(),
            returncode=process.returncode or 1 # should never be None
        )

class CopyTask(Task):
    result: TaskResult
    src_path: str
    src_container: str
    dst_path: str
    dst_container: str

    def __init__(self,
                 name: str,
                 src_path: str,
                 dst_path: str,
                 src_container: str = '',
                 dst_container: str = '',
                 deps: list['Task'] | None = None):
        super().__init__(name, deps)
        self.src_path = src_path
        self.src_container = src_container
        self.dst_path = dst_path
        self.dst_container = dst_container

    @override
    async def _run(self):
        cmd = 'cp'
        if self.src_container or self.dst_container:
            cmd = 'docker cp'
        source = f'dn.{self.src_container}:{self.src_path}' if self.src_container else self.src_path
        destination = f'dn.{self.dst_container}:{self.dst_path}' if self.dst_container else self.dst_path
        cmd = f'{cmd} {source} {destination}'
        process = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        self.result = TaskResult(
            stdout=stdout.decode().strip(),
            stderr=stderr.decode().strip(),
            returncode=process.returncode or 1 # should never be None
        )


class TaskScheduler:
    tasks: dict[str, Task]

    def __init__(self):
        self.tasks = {}

    async def run(self):
        _ = await asyncio.gather(*(task.run() for task in self.tasks.values()))

    def add_task(self,
                 name: str,
                 action: str,
                 container: str = '',
                 deps: list[str] | None = None):
        dependencies = [self.tasks[dep] for dep in deps] if deps else None
        self.tasks[name] = CmdTask(name, action, container, deps=dependencies)

    def add_copy_task(self,
                     name: str,
                     src_path: str,
                     dst_path: str,
                     src_container: str = '',
                     dst_container: str = '',
                     deps: list[str] | None = None):
        dependencies = [self.tasks[dep] for dep in deps] if deps else None
        self.tasks[name] = CopyTask(name,
                                    src_path,
                                    dst_path,
                                    src_container,
                                    dst_container,
                                    deps=dependencies)

