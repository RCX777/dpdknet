import subprocess

def run_command_throw(command: list[str]) -> str:
    r = subprocess.run(command, capture_output=True, text=True)
    if r.returncode != 0:
        print(f'Error running {' '.join(command)}: {r.stderr.strip()}')
        raise subprocess.CalledProcessError(r.returncode, command)
    return r.stdout.strip()

def run_command(command: list[str]) -> tuple[str, int]:
    r = subprocess.run(command, capture_output=True, text=True)
    stream = r.stdout
    if r.returncode != 0:
        stream = r.stderr
    return stream.strip(), r.returncode

