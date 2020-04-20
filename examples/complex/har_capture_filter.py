import json
import base64
import typing
import tempfile

from datetime import datetime
from datetime import timezone
import dateutil.parser

from enum import Enum, auto

import falcon

from mitmproxy import ctx

from mitmproxy import connections
from mitmproxy import version
from mitmproxy.utils import strutils
from mitmproxy.net.http import cookies

# A list of server seen till now is maintained so we can avoid
# using 'connect' time for entries that use an existing connection.
SERVERS_SEEN: typing.Set[connections.ServerConnection] = set()

DEFAULT_PAGE_REF = "Default"
DEFAULT_PAGE_TITLE = "Default"


class HarCaptureFilter:

    def __init__(self):
        self.num = 0
        self.har = None
        self.har_page_count = 0
        self.har_capture_types = []
        self.current_har_page = None

    def request(self, flow):
        print()

    def response(self, flow):
        print()

