import os
import random
import socket
import time
from datetime import datetime

target: str = os.environ.get("TARGET", "hf1")
port = int(os.environ.get("PORT", "5514"))
proto: str = os.environ.get("PROTO", "udp")

if proto == "tcp":
    sock: socket.socket = socket.create_connection((target, port))
else:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

action: list[str] = ["login", "logout", "fail"]
while True:
    ts: str = datetime.now().astimezone().strftime("%b %d %H:%M:%S %z")
    msg: str = f"{ts} event=USER_AUTH user={random.randint(1, 5)} action={random.choice(action)}"

    if proto == "tcp":
        sock.sendall((msg + "\n").encode())
    else:
        sock.sendto(msg.encode(), (target, port))
    time.sleep(random.uniform(0, 10))
