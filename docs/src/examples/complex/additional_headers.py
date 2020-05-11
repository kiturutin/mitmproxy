import json
import base64
import typing
import tempfile

import re

from datetime import datetime
from datetime import timezone

import falcon

from mitmproxy import ctx

from mitmproxy import connections
from mitmproxy import version
from mitmproxy.utils import strutils
from mitmproxy.net.http import cookies
from mitmproxy import http

# A list of server seen till now is maintained so we can avoid
# using 'connect' time for entries that use an existing connection.
SERVERS_SEEN: typing.Set[connections.ServerConnection] = set()

DEFAULT_PAGE_REF = "Default"
DEFAULT_PAGE_TITLE = "Default"


class AddHeadersResource:

    def addon_path(self):
        return "additional_headers"

    def __init__(self, additional_headers_addon):
        self.num = 0
        self.additional_headers_addon = additional_headers_addon

    def on_get(self, req, resp, method_name):
        getattr(self, "on_" + method_name)(req, resp)

    def on_add_headers(self, req, resp):
        for k, v in req.params.items():
            self.additional_headers_addon.headers[k] = v


    def on_add_header(self, req, resp):
        for k, v in req.params.items():
            self.additional_headers_addon.headers[k] = v

    def on_remove_header(self, req, resp):
        self.additional_headers_addon.headers.pop(req.get_param('name'))

    def on_remove_all_headers(self, req, resp):
        self.additional_headers_addon.headers = {}

class AddHeadersAddOn:

    def __init__(self):
        self.num = 0
        self.headers = {}

    def get_resource(self):
        return AddHeadersResource(self)

    def request(self, flow):
        for k, v in self.headers.items():
            flow.request.headers[k] = v


addons = [
    AddHeadersAddOn()
]
