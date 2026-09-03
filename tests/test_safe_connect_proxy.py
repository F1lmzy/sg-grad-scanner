import socket

import safe_connect_proxy as proxy


def test_proxy_rejects_any_private_dns_answer(monkeypatch):
    answers = [
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443)),
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 443)),
    ]
    monkeypatch.setattr(proxy.socket, "getaddrinfo", lambda *args, **kwargs: answers)

    try:
        proxy.resolve_public("rebind.example", 443)
    except proxy.UnsafeDestination:
        pass
    else:
        raise AssertionError("mixed public/private DNS answers were accepted")


def test_proxy_returns_pinned_public_sockaddrs(monkeypatch):
    answers = [
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443)),
    ]
    monkeypatch.setattr(proxy.socket, "getaddrinfo", lambda *args, **kwargs: answers)

    assert proxy.resolve_public("example.com", 443)[0][3][0] == "93.184.216.34"
