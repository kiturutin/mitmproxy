import typing

from mitmproxy import controller
from mitmproxy import flow
from mitmproxy import http
from mitmproxy import tcp
from mitmproxy import websocket

Events = frozenset([
    "clientconnect",
    "clientdisconnect",
    "serverconnect",
    "serverdisconnect",
    "proxy_to_server_connection_succeeded",
    # TCP
    "tcp_start",
    "tcp_message",
    "tcp_error",
    "tcp_end",
    "tcp_resolving_server_address_started",
    "tcp_resolving_server_address_finished",
    #SSL
    "ssl_handshake_started",
    "ssl_handshake_finished",
    # HTTP
    "http_connect",
    "request",
    "requestheaders",
    "response",
    "responseheaders",
    "http_proxy_to_server_request_started",
    "http_proxy_to_server_request_finished",
    "http_server_to_proxy_response_receiving",
    "http_server_to_proxy_response_received",
    "error",
    # WebSocket
    "websocket_handshake",
    "websocket_start",
    "websocket_message",
    "websocket_error",
    "websocket_end",
    # misc
    "next_layer",
    "configure",
    "done",
    "log",
    "load",
    "running",
    "update",
])

TEventGenerator = typing.Iterator[typing.Tuple[str, typing.Any]]


def _iterate_http(f: http.HTTPFlow) -> TEventGenerator:
    if f.request:
        yield "requestheaders", f
        yield "request", f
    if f.response:
        yield "responseheaders", f
        yield "response", f
    if f.error:
        yield "error", f


def _iterate_websocket(f: websocket.WebSocketFlow) -> TEventGenerator:
    messages = f.messages
    f.messages = []
    f.reply = controller.DummyReply()
    yield "websocket_start", f
    while messages:
        f.messages.append(messages.pop(0))
        yield "websocket_message", f
    if f.error:
        yield "websocket_error", f
    yield "websocket_end", f


def _iterate_tcp(f: tcp.TCPFlow) -> TEventGenerator:
    messages = f.messages
    f.messages = []
    f.reply = controller.DummyReply()
    yield "tcp_start", f
    while messages:
        f.messages.append(messages.pop(0))
        yield "tcp_message", f
    if f.error:
        yield "tcp_error", f
    yield "tcp_end", f


_iterate_map: typing.Dict[typing.Type[flow.Flow], typing.Callable[[typing.Any], TEventGenerator]] = {
    http.HTTPFlow: _iterate_http,
    websocket.WebSocketFlow: _iterate_websocket,
    tcp.TCPFlow: _iterate_tcp,
}


def iterate(f: flow.Flow) -> TEventGenerator:
    try:
        e = _iterate_map[type(f)]
    except KeyError as err:
        raise TypeError("Unknown flow type: {}".format(f)) from err
    else:
        yield from e(f)
