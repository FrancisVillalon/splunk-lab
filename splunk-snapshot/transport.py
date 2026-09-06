import shlex
import subprocess
from dataclasses import dataclass

DEFAULT_TIMEOUT = 30
BTOOL_TIMEOUT = 120


class TransportError(Exception):
    pass


@dataclass
class Result:
    returncode: int
    stdout: str
    stderr: str
