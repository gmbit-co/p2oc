from tempfile import NamedTemporaryFile
from typing import NamedTuple

import bitcoin.rpc


class Config(NamedTuple):
    rpcuser: str = "username"
    rpcpassword: str = "password"
    rpcconnect: str = "0.0.0.0"
    rpcport: int = 8332

    def asfilestr(self):
        return f"""
rpcuser={self.rpcuser}
rpcpassword={self.rpcpassword}
rpcport={self.rpcport}
rpcconnect={self.rpcconnect}
"""


class Proxy:
    """Simple proxy class to bitcoin.rpc.Proxy to deal with timeouts"""

    def __init__(self, config=None):
        if config is None:
            config = Config()
        self._conf_file = NamedTemporaryFile(mode="w+t")
        self._conf_file.write(config.asfilestr())
        self._conf_file.seek(0)

    @property
    def _proxy(self):
        return bitcoin.rpc.Proxy(btc_conf_file=self._conf_file.name, timeout=3600)

    def __getattr__(self, name):
        if name.startswith("_"):
            return getattr(self, name)
        return getattr(self._proxy, name)

    def createwallet(self, wallet_name, *args):
        return self._proxy._call("createwallet", wallet_name, *args)

    def loadwallet(self, wallet_name, *args):
        return self._proxy._call("loadwallet", wallet_name, *args)

    def unloadwallet(self, wallet_name, *args):
        return self._proxy._call("unloadwallet", wallet_name, *args)

    def __del__(self):
        self._conf_file.close()
