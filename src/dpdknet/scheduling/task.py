import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import override

from dpdknet.domain.net.host import Host

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
    host: Host | None

    def __init__(self,
                 name: str,
                 cmd: str,
                 host: Host | None = None,
                 deps: list['Task'] | None = None):
        super().__init__(name, deps)
        self.cmd = cmd
        self.host = host

    @override
    async def _run(self):
        if self.host:
            if not self.host.started:
                raise RuntimeError(f'[task] Host "{self.host.name}" is not started.')
            cmd = f'docker exec -it {self.host.container_name} bash -c "{self.cmd}"'
        else:
            cmd = self.cmd
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

class CopyTask(Task):
    result: TaskResult
    src_path: str
    src_container: Host | None
    dst_path: str
    dst_container: Host | None

    def __init__(self,
                 name: str,
                 src_path: str,
                 dst_path: str,
                 src_container: Host | None = None,
                 dst_container: Host | None = None,
                 deps: list['Task'] | None = None):
        super().__init__(name, deps)
        self.src_path = src_path
        self.src_container = src_container
        self.dst_path = dst_path
        self.dst_container = dst_container

    @override
    async def _run(self):
        if self.src_container is None:
            if self.dst_container is None:
                cmd = f'cp {self.src_path} {self.dst_path}'
            else:
                cmd = f'docker cp {self.src_path} {self.dst_container.container_name}:{self.dst_path}'
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
        else:
            await self.src_container.copy_file(
                self.src_path,
                self.dst_path,
                dst_host=self.dst_container
            )


class TaskScheduler:
    tasks: dict[str, Task]

    def __init__(self):
        self.tasks = {}

    async def run(self):
        _ = await asyncio.gather(*(task.run() for task in self.tasks.values()))

    def add_task(self, task: Task):
        if task.name in self.tasks:
            raise ValueError(f'Task with name {task.name} already exists.')
        self.tasks[task.name] = task

