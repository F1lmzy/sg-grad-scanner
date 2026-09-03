#!/usr/bin/env python3
"""Minimal CONNECT proxy that pins DNS to validated public IP addresses."""

import contextlib
import ipaddress
import select
import socket
import socketserver
import threading
import urllib.parse


class UnsafeDestination(ValueError):
    pass


def resolve_public(hostname, port):
    addresses = socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
    if not addresses:
        raise UnsafeDestination("destination did not resolve")
    validated = []
    for family, socktype, proto, _, sockaddr in addresses:
        address = ipaddress.ip_address(sockaddr[0])
        if not address.is_global:
            raise UnsafeDestination(f"non-public destination blocked: {address}")
        validated.append((family, socktype, proto, sockaddr))
    return validated


def connect_pinned(hostname, port, timeout=15):
    last_error = None
    for family, socktype, proto, sockaddr in resolve_public(hostname, port):
        peer = socket.socket(family, socktype, proto)
        peer.settimeout(timeout)
        try:
            peer.connect(sockaddr)
            peer.settimeout(None)
            return peer
        except OSError as error:
            last_error = error
            peer.close()
    raise OSError(f"could not connect to validated destination: {last_error}")


def _relay(left, right):
    sockets = [left, right]
    while sockets:
        readable, _, exceptional = select.select(sockets, [], sockets, 30)
        if exceptional or not readable:
            return
        for source in readable:
            data = source.recv(65536)
            if not data:
                return
            destination = right if source is left else left
            destination.sendall(data)


class SafeConnectHandler(socketserver.StreamRequestHandler):
    def handle(self):
        line = self.rfile.readline(8193)
        if len(line) > 8192:
            return
        parts = line.decode("latin1", "replace").strip().split(" ", 2)
        if len(parts) != 3 or parts[0].upper() != "CONNECT":
            self.wfile.write(b"HTTP/1.1 405 CONNECT Required\r\nConnection: close\r\n\r\n")
            return
        parsed = urllib.parse.urlsplit("//" + parts[1])
        host = parsed.hostname
        port = parsed.port or 443
        if not host or port != 443:
            self.wfile.write(b"HTTP/1.1 403 Forbidden\r\nConnection: close\r\n\r\n")
            return
        total = 0
        while True:
            header = self.rfile.readline(8193)
            total += len(header)
            if not header or header in (b"\r\n", b"\n") or total > 65536:
                break
        try:
            peer = connect_pinned(host, port)
        except (OSError, UnsafeDestination, ValueError):
            self.wfile.write(b"HTTP/1.1 403 Forbidden\r\nConnection: close\r\n\r\n")
            return
        try:
            self.wfile.write(b"HTTP/1.1 200 Connection Established\r\n\r\n")
            self.wfile.flush()
            _relay(self.connection, peer)
        finally:
            peer.close()


class SafeConnectProxy(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


@contextlib.contextmanager
def safe_proxy():
    server = SafeConnectProxy(("127.0.0.1", 0), SafeConnectHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
