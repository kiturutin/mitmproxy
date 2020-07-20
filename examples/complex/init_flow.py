import json
import base64
import typing
import tempfile

from time import sleep
import mitmproxy.tcp
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

class InitFlowResource:

    def addon_path(self):
        return "init_flow"

    def __init__(self, init_flow_addon):
        self.init_flow_addon = init_flow_addon
        for a in ctx.master.addons.get("scriptloader").addons:
            if 'har_dump.py' in a.fullpath:
                self.init_flow_addon.har_dump_addon = a.addons[0].addons[0]

    def on_get(self, req, resp, method_name):
        getattr(self, "on_" + method_name)(req, resp)


class InitFlowAddOn:

    def __init__(self):
        self.num = 0
        self.har_dump_addon = None

    def get_resource(self):
        return InitFlowResource(self)

    def http_connect(self, flow):
        ctx.log.debug('Incoming CONNECT request: {}'.format(str(flow.request)))

        if not hasattr(flow.server_conn, 'currentHarEntry'):
            self.init_har_entry(flow)
        else:
            ctx.log.debug('Found flow data for request: {}, har entry is: {}'.format(str(flow.request), str(flow.server_conn.currentHarEntry)))

    def request(self, flow):
        ctx.log.debug('Incoming HTTP request: {}'.format(str(flow.request)))

        if not hasattr(flow.server_conn, 'currentHarEntry'):
            self.init_har_entry(flow)
        else:
            ctx.log.debug('Found flow data for request: {}, har entry is: {}'.format(str(flow.request), str(flow.server_conn.currentHarEntry)))

    def tcp_start(self, flow):
        print()

    def init_har_entry(self, flow):
        ctx.log.debug("Initializing har entry for flow: {}".format(str(flow.request)))

        setattr(flow.server_conn, 'currentHarEntry', self.har_dump_addon.generate_har_entry())
        self.har_dump_addon.append_har_entry(flow.server_conn.currentHarEntry)

addons = [
    InitFlowAddOn()
]
