#!/usr/bin/env python3
"""Measure PostgreSQL round-trip time to one server address (stdlib only).

Runs on the host or, embedded in a Workspace Exec, inside a guest: resolve the
address, open fresh connections (TCP connect, one SSLRequest probe that a
plaintext server answers `N`, startup to ReadyForQuery), then time a loop of
simple-protocol `SELECT 1` on one connection. Authentication is trust or
SCRAM-SHA-256 with the password from an environment variable; the password is
never an argument. Python 3.9 compatible. Prints one JSON object.
"""

import argparse
import base64
import hashlib
import hmac
import json
import os
import platform
import secrets
import socket
import struct
import time


def stats(values):
    ordered = sorted(values)
    if not ordered:
        return None
    middle = len(ordered) // 2
    median = (
        ordered[middle]
        if len(ordered) % 2
        else (ordered[middle - 1] + ordered[middle]) // 2
    )
    rank = max(0, -(-len(ordered) * 9 // 10) - 1)  # nearest-rank p90
    return {
        "n": len(ordered),
        "median_ns": median,
        "p90_ns": ordered[rank],
        "min_ns": ordered[0],
        "max_ns": ordered[-1],
        "mean_ns": sum(ordered) // len(ordered),
    }


def receive(sock, count):
    data = b""
    while len(data) < count:
        chunk = sock.recv(count - len(data))
        if not chunk:
            raise ConnectionError("server closed the connection")
        data += chunk
    return data


def message(sock):
    kind = receive(sock, 1)
    (length,) = struct.unpack("!I", receive(sock, 4))
    return kind, receive(sock, length - 4)


def send(sock, kind, payload):
    sock.sendall(kind + struct.pack("!I", len(payload) + 4) + payload)


def scram(sock, user, password, body):
    if b"SCRAM-SHA-256" not in body.split(b"\0"):
        raise ConnectionError("server offers no SCRAM-SHA-256")
    nonce = base64.b64encode(secrets.token_bytes(18)).decode()
    first_bare = f"n=,r={nonce}"
    initial = ("n,," + first_bare).encode()
    send(
        sock,
        b"p",
        b"SCRAM-SHA-256\0" + struct.pack("!I", len(initial)) + initial,
    )
    kind, body = message(sock)
    if kind != b"R" or struct.unpack("!I", body[:4])[0] != 11:
        raise ConnectionError("expected SASL continue")
    server_first = body[4:].decode()
    fields = dict(item.split("=", 1) for item in server_first.split(","))
    salted = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), base64.b64decode(fields["s"]), int(fields["i"])
    )
    client_key = hmac.new(salted, b"Client Key", "sha256").digest()
    stored = hashlib.sha256(client_key).digest()
    final_bare = f"c=biws,r={fields['r']}"
    auth = f"{first_bare},{server_first},{final_bare}".encode()
    signature = hmac.new(stored, auth, "sha256").digest()
    proof = base64.b64encode(bytes(a ^ b for a, b in zip(client_key, signature)))
    send(sock, b"p", f"{final_bare},p=".encode() + proof)
    kind, body = message(sock)
    if kind != b"R" or struct.unpack("!I", body[:4])[0] != 12:
        raise ConnectionError("expected SASL final")


def startup(sock, user, database, password):
    parameters = b"".join(
        key.encode() + b"\0" + value.encode() + b"\0"
        for key, value in (("user", user), ("database", database))
    )
    payload = struct.pack("!I", 196608) + parameters + b"\0"
    sock.sendall(struct.pack("!I", len(payload) + 4) + payload)
    while True:
        kind, body = message(sock)
        if kind == b"R":
            code = struct.unpack("!I", body[:4])[0]
            if code == 10:
                if password is None:
                    raise ConnectionError("server asks for SCRAM; no password")
                scram(sock, user, password, body[4:])
            elif code != 0:
                raise ConnectionError(f"unsupported authentication {code}")
        elif kind == b"E":
            raise ConnectionError(body.replace(b"\0", b" ").decode(errors="replace"))
        elif kind == b"Z":
            return


def connect_once(address, user, database, password, timeout):
    """One fresh connection; returns (socket, tcp_ns, ssl_probe_ns, startup_ns)."""
    started = time.perf_counter_ns()
    sock = socket.create_connection(address, timeout=timeout)
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    connected = time.perf_counter_ns()
    sock.sendall(struct.pack("!II", 8, 80877103))  # SSLRequest
    answer = receive(sock, 1)
    probed = time.perf_counter_ns()
    if answer != b"N":
        sock.close()
        raise ConnectionError("server accepted TLS; the probe expects plaintext")
    startup(sock, user, database, password)
    ready = time.perf_counter_ns()
    return sock, connected - started, probed - connected, ready - probed


def query_loop(sock, iterations):
    rounds = []
    query = b"SELECT 1\0"
    for _ in range(iterations):
        started = time.perf_counter_ns()
        send(sock, b"Q", query)
        while True:
            kind, _ = message(sock)
            if kind == b"Z":
                break
        rounds.append(time.perf_counter_ns() - started)
    return rounds


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", required=True)
    parser.add_argument("--port", type=int, default=5432)
    parser.add_argument("--user", required=True)
    parser.add_argument("--database", required=True)
    parser.add_argument("--password-env")
    parser.add_argument("--iterations", type=int, default=200)
    parser.add_argument("--connects", type=int, default=20)
    parser.add_argument("--timeout", type=float, default=5.0)
    args = parser.parse_args(argv)
    password = os.environ.get(args.password_env) if args.password_env else None
    started = time.perf_counter_ns()
    infos = socket.getaddrinfo(args.host, args.port, type=socket.SOCK_STREAM)
    resolve_ns = time.perf_counter_ns() - started
    result = {
        "tool": "pgrtt-v1",
        "target": {"host": args.host, "port": args.port, "user": args.user},
        "client": {
            "hostname": socket.gethostname(),
            "system": platform.system(),
            "machine": platform.machine(),
            "python": platform.python_version(),
        },
        "authentication": "scram-sha-256" if password else "trust",
        "resolve_ns": resolve_ns,
        "resolved": [info[4][0] for info in infos],
        "note": "create_connection resolves and tries addresses in order, as the product driver does",
    }
    tcp, probe, setup = [], [], []
    for _ in range(args.connects):
        sock, a, b, c = connect_once(
            (args.host, args.port), args.user, args.database, password, args.timeout
        )
        tcp.append(a)
        probe.append(b)
        setup.append(c)
        sock.sendall(b"X\0\0\0\4")
        sock.close()
    sock, *_ = connect_once(
        (args.host, args.port), args.user, args.database, password, args.timeout
    )
    result["peer"] = sock.getpeername()[0]
    rounds = query_loop(sock, args.iterations)
    sock.sendall(b"X\0\0\0\4")
    sock.close()
    result.update(
        tcp_connect=stats(tcp),
        ssl_probe=stats(probe),
        startup_to_ready=stats(setup),
        select1=stats(rounds),
    )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
