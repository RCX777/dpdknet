import subprocess
import asyncio


async def run_command_throw(command: list[str]) -> tuple[int, str]:
    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    returncode: int = process.returncode if process.returncode is not None else 1
    if returncode != 0:
        raise subprocess.CalledProcessError(returncode,
                                            command,
                                            output=stdout,
                                            stderr=stderr)
    return returncode, stdout.decode().strip()


async def run_command(command: list[str]) -> tuple[int, str]:
    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    returncode: int = process.returncode if process.returncode is not None else 1
    if returncode != 0:
        return returncode, stderr.decode().strip()
    return returncode, stdout.decode().strip()

