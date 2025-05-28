import subprocess
import time
from collections.abc import Callable


def run_command_throw(command: list[str]) -> tuple[int, str]:
    r = subprocess.run(command, capture_output=True, text=True, check=False)
    if r.returncode != 0:
        print(f'Error running {" ".join(command)}: {r.stderr.strip()}')
        raise subprocess.CalledProcessError(r.returncode, command)
    return r.returncode, r.stdout.strip()


def run_command(command: list[str]) -> tuple[int, str]:
    r = subprocess.run(command, capture_output=True, text=True, check=False)
    stream = r.stdout
    if r.returncode != 0:
        stream = r.stderr
    return r.returncode, stream.strip()


def wait_for_command_success(
    command: list[str],
    interval: float = 0.2,
    timeout: float = 10.0,
    runner: Callable[[list[str]], tuple[int, str]] = run_command,
) -> str:
    start_time = time.time()
    while True:
        if time.time() - start_time > timeout:
            raise TimeoutError(f'Command `{" ".join(command)}` timed out after {timeout} seconds.')
        returncode, output = runner(command)
        if returncode == 0:
            return output
        time.sleep(interval)
