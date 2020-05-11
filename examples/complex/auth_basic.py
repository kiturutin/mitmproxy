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


class AuthBasicResource:

    def addon_path(self):
        return "auth_basic"

    def __init__(self, auth_basic_addon):
        self.num = 0
        self.auth_basic_addon = auth_basic_addon

    def on_get(self, req, resp, method_name):
        getattr(self, "on_" + method_name)(req, resp)

    def on_auth_authorization(self, req, resp):
        credentials = req.get_param('base64EncodedCredentials')
        domain = req.get_param('domain')
        self.auth_basic_addon.credentials_map[domain] = credentials

    def on_stop_authorization(self, req, resp):
        domain = req.get_param('domain')
        self.auth_basic_addon.credentials_map.pop(domain)

class AuthBasicAddOn:

    def __init__(self):
        self.num = 0
        self.credentials_map = {}

    def get_resource(self):
        return AuthBasicResource(self)

    def request(self, flow):
        if flow.request.host in self.credentials_map:
            flow.request.headers['Authorization'] = 'Basic ' + self.credentials_map[flow.request.host]


addons = [
    AuthBasicAddOn()
]
