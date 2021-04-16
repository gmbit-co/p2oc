from tempfile import NamedTemporaryFile
from typing import NamedTuple
import bitcoin.rpc


class Config(NamedTuple):
    rpcuser: str = 'username'
    rpcpassword: str = 'password'
    rpcconnect: str = '0.0.0.0'
    rpcport: int = 8332

    def asfilestr(self):
        return (
f"""
rpcuser={self.rpcuser}
rpcpassword={self.rpcpassword}
rpcport={self.rpcport}
rpcconnect={self.rpcconnect}
"""
        )

class Proxy:
    """Simple proxy class to bitcoin.rpc.Proxy to deal with timeouts"""

    def __init__(self, config=None):
        if config is None:
            config = Config()
        self._conf_file = NamedTemporaryFile(mode="w+t")
        print(config.asfilestr())
        self._conf_file.write(config.asfilestr())
        self._conf_file.seek(0)

    def __getattr__(self, name):
        if name.startswith("_"):
            return getattr(self, name)

        proxy = bitcoin.rpc.Proxy(btc_conf_file=self._conf_file.name, timeout=3600)
        self._proxy = proxy  # DEBUG
        return getattr(proxy, name)

    def __del__(self):
        self._conf_file.close()
