from time import time
from OpenSSL.SSL import WantWriteError, WantReadError
from mitmproxy.exceptions import TcpTimeout


class TimeoutHelper:

    @staticmethod
    def wrap_with_timeout(openssl_callable, timeout):
        start = time()
        while True:
            try:
                return openssl_callable()
            except (WantReadError, WantWriteError):
                if timeout is None or time() - start >= timeout:
                    raise TcpTimeout
