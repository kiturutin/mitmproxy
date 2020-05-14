import time

from mitmproxy import ctx
from mitmproxy.exceptions import TcpTimeout

RESOLUTION_FAILED_ERROR_MESSAGE = "Unable to resolve host: "
CONNECTION_FAILED_ERROR_MESSAGE = "Unable to connect to host"
RESPONSE_TIMED_OUT_ERROR_MESSAGE = "Response timed out"


class HttpConnectCaptureResource:

    def addon_path(self):
        return "http_connect_capture"

    def __init__(self, har_connect_addon):
        self.num = 0
        self.har_connect_addon = har_connect_addon
        for a in ctx.master.addons.get("scriptloader").addons:
            if 'har_dump.py' in a.fullpath:
                self.har_connect_addon.har_dump_addon = a.addons[0].addons[0]

    def on_get(self, req, resp, method_name):
        getattr(self, "on_" + method_name)(req, resp)


class HttpConnectCaptureAddOn:

    def __init__(self):
        self.num = 0
        self.har_dump_addon = None

        self.dns_resolution_started_nanos = 0
        self.connection_started_nanos = 0
        self.send_started_nanos = 0
        self.send_finished_nanos = 0
        self.response_receive_started_nanos = 0
        self.ssl_handshake_started_nanos = 0

    # TCP Callbacks

    def tcp_resolving_server_address_finished(self, sever_conn):
        self.populate_dns_timings()

    def tcp_resolving_server_address_started(self, sever_conn):
        self.dns_resolution_started_nanos = int(round(time.time() * 1000000))
        self.connection_started_nanos = int(round(time.time() * 1000000))


    # SSL Callbacks
    def ssl_handshake_started(self, flow):
        self.ssl_handshake_started_nanos = int(round(time.time() * 1000000))

    # HTTP Callbacks

    def http_proxy_to_server_request_started(self, flow):
        self.send_started_nanos = time.time() * 1000000

    def http_proxy_to_server_request_finished(self, flow):
        self.send_finished_nanos = time.time() * 1000000
        if self.send_started_nanos > 0:
            self.get_har_entry()['timings'][
                'send'] = self.send_finished_nanos - self.send_started_nanos
        else:
            self.get_har_entry()['timings']['send'] = 0

    def http_server_to_proxy_response_receiving(self, flow):
        self.response_receive_started_nanos = time.time() * 1000000

    def http_server_to_proxy_response_received(self, flow):
        """"""

    # PROXY Callbacks

    def error(self, flow):
        req_host_port = flow.request.host
        if flow.request.port != 80 and flow.request.port != 443:
            req_host_port = req_host_port + ':' + str(flow.request.port)
        original_error = HttpConnectCaptureAddOn.get_original_exception(
            flow.error)

        if 'Name or service not known' in str(original_error):
            self.proxy_to_server_resolution_failed(flow, req_host_port,
                                                   original_error)
        elif isinstance(original_error, TcpTimeout):
            self.server_to_proxy_response_timed_out(flow, req_host_port,
                                                    original_error)
        else:
            self.proxy_to_server_connection_failed(flow, original_error)

    # Populate data

    def populate_dns_timings(self):
        if self.dns_resolution_started_nanos > 0 and self.get_har_entry():
            dns_nanos = int(round(
                time.time() * 1000000)) - self.dns_resolution_started_nanos
            dns_ms = int(dns_nanos / 1000)
            self.get_har_entry()['timings']['dns'] = dns_ms

    def populate_timings_for_failed_connect(self):
        if self.connection_started_nanos > 0:
            self.get_har_entry()['timings']['connect'] = int(
                round(time.time() * 1000000)) - self.connection_started_nanos
        self.populate_dns_timings()

    def populate_server_ip_address(self, flow, original_error):
        if isinstance(original_error, (ConnectionRefusedError, TcpTimeout)):
            if flow.server_conn and flow.server_conn.ip_address:
                self.get_har_entry()['serverIPAddress'] = str(
                    flow.server_conn.ip_address[0])

    def get_resource(self):
        return HttpConnectCaptureResource(self)

    def proxy_to_server_resolution_failed(self, flow, req_host_port,
                                          original_error):
        msg = RESOLUTION_FAILED_ERROR_MESSAGE + req_host_port
        self.create_har_entry_for_failed_connect(flow.request, msg)
        self.populate_dns_timings()
        self.populate_server_ip_address(flow, original_error)

        self.get_har_entry()['time'] = self.calculate_total_elapsed_time()

    def proxy_to_server_connection_failed(self, flow, original_error):
        msg = CONNECTION_FAILED_ERROR_MESSAGE
        self.create_har_entry_for_failed_connect(flow.request, msg)
        self.populate_timings_for_failed_connect()
        self.populate_server_ip_address(flow, original_error)

        self.get_har_entry()['time'] = self.calculate_total_elapsed_time()

    def server_to_proxy_response_timed_out(self, flow, req_host_port,
                                           original_error):
        msg = RESPONSE_TIMED_OUT_ERROR_MESSAGE
        self.create_har_entry_for_failed_connect(flow.request, msg)
        self.populate_timings_for_failed_connect()
        self.populate_server_ip_address(flow, original_error)

        current_time_nanos = time.time() * 1000000

        if self.send_started_nanos > 0 and self.send_finished_nanos == 0:
            self.get_har_entry()['timings'][
                'send'] = current_time_nanos - self.send_started_nanos

        elif self.send_finished_nanos > 0 and self.response_receive_started_nanos == 0:
            self.get_har_entry()['timings'][
                'wait'] = current_time_nanos - self.send_finished_nanos

        elif self.response_receive_started_nanos > 0:
            self.get_har_entry()['timings'][
                'receive'] = current_time_nanos - self.response_receive_started_nanos

        self.get_har_entry()['time'] = self.calculate_total_elapsed_time()

    def create_har_entry_for_failed_connect(self, request, msg):
        if not self.get_har_entry():
            self.har_dump_addon.create_har_entry_with_default_response(request)

        self.get_har_entry()['response']['_errorMessage'] = msg

    def calculate_total_elapsed_time(self):
        timings = self.get_har_entry()['timings']
        result = (0 if timings['blocked'] == -1 else timings['blocked']) + \
                 (0 if timings['dns'] == -1 else timings['dns']) + \
                 (0 if timings['connect'] == -1 else timings['connect']) + \
                 (0 if timings['send'] == -1 else timings['send']) + \
                 (0 if timings['wait'] == -1 else timings['wait']) + \
                 (0 if timings['receive'] == -1 else timings['receive'])
        return result

    def get_har_entry(self):
        return self.har_dump_addon.har_entry

    @staticmethod
    def get_original_exception(flow_error):
        result = flow_error.cause
        while True:
            if hasattr(result, '__cause__') and result.__cause__:
                result = result.__cause__
            else:
                break
        return result


addons = [
    HttpConnectCaptureAddOn()
]
