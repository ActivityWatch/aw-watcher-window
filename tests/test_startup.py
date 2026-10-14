"""Startup integration tests with the real client and its persistent queue.

The watcher must start recording while aw-server is still starting (slow
boots), instead of exiting after aw-client's 10 s wait_for_start() timeout.
"""

import json
import socket
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest
import requests
from aw_client import ActivityWatchClient

import aw_watcher_window.main as main_module


class OfflineServer:
    """Patches the transport so the server is down until ``available`` is set."""

    def __init__(self):
        self.available = threading.Event()
        self.offline_attempt = threading.Event()
        self.delivered = threading.Event()
        self.expected_heartbeats = 0
        self.requests = []
        self.stop = threading.Event()

    def request(self, method, url, **kwargs):
        if not self.available.is_set():
            self.offline_attempt.set()
            # Bound cleanup if a regression blocks in wait_for_start(), before
            # the watcher reaches the interruptible poll loop.
            if self.stop.is_set() and method.upper() == "GET":
                raise KeyboardInterrupt
            raise requests.ConnectionError("server has not started")
        payload = json.loads(kwargs.get("data") or b"{}")
        self.requests.append((method.upper(), url, payload))
        heartbeats = sum("/heartbeat" in request[1] for request in self.requests)
        if self.expected_heartbeats and heartbeats == self.expected_heartbeats:
            self.delivered.set()
        response = requests.Response()
        response.status_code = 200
        response._content = b"{}"
        return response


@pytest.fixture
def startup(tmp_path, monkeypatch):
    # Isolate config, instance locks and SQLite queues, including the
    # replacement queue created by client.disconnect().
    for name in ("data", "cache", "config"):
        monkeypatch.setattr(
            "aw_core.dirs.platformdirs.user_" + name + "_dir",
            lambda *args, _name=name, **kwargs: str(Path(tmp_path) / _name),
        )

    server = OfflineServer()
    monkeypatch.setattr("requests.sessions.Session.request", server.request)

    clients = []

    class Client(ActivityWatchClient):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.request_queue._attempt_reconnect_interval = 0.01
            self.original_queue = self.request_queue
            clients.append(self)

    sampled = threading.Event()
    stop = server.stop
    windows = iter(
        [
            {"app": "editor", "title": "one"},
            {"app": "editor", "title": "two"},
            {"app": "browser", "title": "three"},
        ]
    )

    def get_current_window(strategy):
        try:
            return next(windows)
        except StopIteration:
            # Every preceding sample has been heartbeated by the real loop.
            sampled.set()
            stop.wait(3)
            raise KeyboardInterrupt

    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]

    monkeypatch.setenv("DISPLAY", ":0")
    monkeypatch.setattr(main_module, "_warn_wayland_once", lambda: None)
    monkeypatch.setattr(main_module, "setup_logging", lambda **kwargs: None)
    monkeypatch.setattr(main_module, "ActivityWatchClient", Client)
    monkeypatch.setattr(main_module, "get_current_window", get_current_window)
    monkeypatch.setattr(main_module, "sleep", lambda seconds: None)
    monkeypatch.setattr(
        main_module,
        "parse_args",
        lambda: SimpleNamespace(
            testing=True,
            verbose=False,
            host="127.0.0.1",
            port=port,
            poll_time=1.0,
            strategy="xlib",
            exclude_title=False,
            exclude_titles=[],
            exclude_apps=[],
            research_enabled=False,
            research_category_map={},
            research_app_category_map={},
        ),
    )

    errors = []

    def run():
        try:
            main_module.main()
        except KeyboardInterrupt:
            # Deliberate shutdown raised by get_current_window() above.
            pass
        except Exception as error:
            errors.append(error)

    thread = threading.Thread(target=run, daemon=True)
    state = SimpleNamespace(
        server=server,
        clients=clients,
        sampled=sampled,
        stop=stop,
        errors=errors,
        thread=thread,
    )
    yield state

    stop.set()
    thread.join(2)
    assert not thread.is_alive(), "watcher leaked from test"
    for client in clients:
        for queue in {client.original_queue, client.request_queue}:
            queue.stop()
            if queue.ident is not None:
                queue.join(2)
            queue._persistqueue.close()
        if hasattr(client.instance, "fp"):
            client.instance.fp.close()


def start_offline(state):
    state.thread.start()
    assert state.server.offline_attempt.wait(1), "no connection attempt"
    # aw-client's wait_for_start() would block for 10 s and then raise
    # "did not start in time" before the first sample.
    assert state.sampled.wait(2), "recording never started while the server was down"
    assert state.errors == []
    assert state.server.requests == []
    queue = state.clients[0].request_queue
    assert queue._persistqueue.qsize() > 0
    return queue


def test_records_offline_then_creates_bucket_before_replaying(startup):
    queue = start_offline(startup)
    # aw-client pre-merges queued heartbeats: each sample is enqueued when the
    # next, different sample arrives, so the newest one stays cached.
    client = startup.clients[0]
    bucket_id = client.client_name + "_" + client.client_hostname
    assert client.last_heartbeat[bucket_id].data == {
        "app": "browser",
        "title": "three",
    }
    assert queue._persistqueue.qsize() == 2
    startup.server.expected_heartbeats = 2
    startup.server.available.set()
    assert startup.server.delivered.wait(2), "queued heartbeats were not replayed"

    requests_ = startup.server.requests
    assert len(requests_) == startup.server.expected_heartbeats + 1
    method, url, payload = requests_[0]
    assert method == "POST"
    assert url.endswith("/buckets/" + bucket_id)
    assert payload["type"] == "currentwindow"
    heartbeats = [payload["data"] for _, url, payload in requests_[1:]]
    assert all("/heartbeat?pulsetime=" in url for _, url, _ in requests_[1:])
    assert heartbeats == [
        {"app": "editor", "title": "one"},
        {"app": "editor", "title": "two"},
    ]


def test_shutdown_offline_preserves_queued_heartbeats(startup):
    queue = start_offline(startup)
    queued = queue._persistqueue.qsize()
    startup.stop.set()
    startup.thread.join(2)
    assert not startup.thread.is_alive(), "offline shutdown blocked"
    assert not queue.is_alive()
    assert startup.errors == []
    # disconnect() constructs a new queue from the same SQLite files.
    reopened = startup.clients[0].request_queue._persistqueue
    assert reopened.qsize() == queued
    first = reopened.get(block=False).data["data"]
    assert first == {"app": "editor", "title": "one"}
