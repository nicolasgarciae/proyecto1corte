#!/usr/bin/env python3
import select
import socket
import sys
import threading


def forward(source: socket.socket, target: socket.socket) -> None:
    try:
        while True:
            ready, _, _ = select.select([source], [], [], 60)
            if not ready:
                continue
            chunk = source.recv(65536)
            if not chunk:
                break
            target.sendall(chunk)
    except OSError:
        pass
    finally:
        try:
            target.shutdown(socket.SHUT_WR)
        except OSError:
            pass


def handle_client(client: socket.socket, target_host: str, target_port: int) -> None:
    upstream = socket.create_connection((target_host, target_port))
    threads = [
        threading.Thread(target=forward, args=(client, upstream), daemon=True),
        threading.Thread(target=forward, args=(upstream, client), daemon=True),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    client.close()
    upstream.close()


def main() -> int:
    if len(sys.argv) != 5:
        print("usage: tcp_bridge.py <listen_host> <listen_port> <target_host> <target_port>")
        return 1

    listen_host = sys.argv[1]
    listen_port = int(sys.argv[2])
    target_host = sys.argv[3]
    target_port = int(sys.argv[4])

    family = socket.AF_INET6 if ":" in listen_host else socket.AF_INET
    server = socket.socket(family, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    if family == socket.AF_INET6:
        try:
            server.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
        except OSError:
            pass
    server.bind((listen_host, listen_port))
    server.listen(100)

    while True:
        client, _ = server.accept()
        threading.Thread(
            target=handle_client,
            args=(client, target_host, target_port),
            daemon=True,
        ).start()


if __name__ == "__main__":
    raise SystemExit(main())
