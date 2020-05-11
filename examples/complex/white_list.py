"""
This inline script can be used to dump flows as HAR files.

example cmdline invocation:
mitmdump -s ./har_dump.py --set hardump=./dump.har

filename endwith '.zhar' will be compressed:
mitmdump -s ./har_dump.py --set hardump=./dump.zhar
"""

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


class WhiteListResource:

    def addon_path(self):
        return "whitelist"

    def __init__(self, white_list_addon):
        self.num = 0
        self.white_list_addon = white_list_addon

    def on_get(self, req, resp, method_name):
        getattr(self, "on_" + method_name)(req, resp)

    def on_whitelist_requests(self, req, resp):
        raw_url_patterns = req.get_param('urlPatterns')
        status_code = req.get_param('statusCode')

        url_patterns = raw_url_patterns.strip("[]").split(",")
        url_patterns_compiled = []

        try:
            for raw_pattern in url_patterns:
                url_patterns_compiled.append(self.parse_regexp(raw_pattern))
        except re.error:
            raise falcon.HTTPBadRequest("Invalid regexp patterns")

        self.white_list_addon.white_list = {
            "status_code": status_code,
            "url_patterns": url_patterns_compiled
        }

    def on_add_whitelist_pattern(self, req, resp):
        url_pattern = req.get_param('urlPattern')

        if not hasattr(self.white_list_addon.white_list, "status_code") \
                or not hasattr(self.white_list_addon.white_list, "url_patterns"):
            raise falcon.HTTPBadRequest("Whitelist is disabled. Cannot add patterns to a disabled whitelist.")

        self.white_list_addon.white_list["url_patterns"].append(url_pattern)

    def on_enable_empty_whitelist(self, req, resp):
        status_code = req.get_param('statusCode')

        self.white_list_addon.white_list["url_patterns"] = []
        self.white_list_addon.white_list["status_code"] = status_code

    def on_disable_whitelist(self, req, resp):
        self.white_list_addon.white_list = {}

    def parse_regexp(self, raw_regexp):
        if not raw_regexp.startswith('^'):
            raw_regexp = '^' + raw_regexp
        if not raw_regexp.endswith('$'):
            raw_regexp = raw_regexp + '$'
        return re.compile(raw_regexp)

class WhiteListAddOn:

    def __init__(self):
        self.num = 0
        self.white_list = {}

    def get_resource(self):
        return WhiteListResource(self)

    def is_whitelist_enabled(self):
        if 'status_code' in self.white_list and 'url_patterns' in self.white_list:
            return True
        return False

    def request(self, flow):
        if not self.is_whitelist_enabled():
            return

        is_whitelisted = False
        for up in self.white_list['url_patterns']:
            if up.match(flow.request.url):
                is_whitelisted = True
                break

        if not is_whitelisted:
            flow.response = http.HTTPResponse.make(
                int(self.white_list['status_code']),
                b"",
                {"Content-Type": "text/html"}
            )
            flow.metadata['WhiteListFiltered'] = True


addons = [
    WhiteListAddOn()
]
