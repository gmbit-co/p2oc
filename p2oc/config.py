import os
import logging
import configparser
from pathlib import Path

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(f"lnd_rpc.py - pid({os.getpid()})")


def _resolve_path(path):
    path = os.path.expanduser(path)
    return str(Path(path).resolve())


DEFAULTS = {
    "rpchost": "localhost:10009",
    "tlscertpath": "~/.lnd/tls.cert",
    "adminmacaroonpath": "~/.lnd/data/chain/bitcoin/testnet/admin.macaroon",
    "network": "testnet",
}


# Consider moving to dataclass
class Config:
    def __init__(self, config_path=None, config_overrides={}):
        config = Config.load_config_or_defaults(config_path)
        config.update(config_overrides)

        self.rpchost = config["rpchost"]
        if self.rpchost.split(":")[0] == "0.0.0.0":
            self.rpchost = self.rpchost.replace("0.0.0.0", "localhost")

        self.tlscertpath = _resolve_path(config["tlscertpath"])
        self.adminmacaroonpath = _resolve_path(config["adminmacaroonpath"])
        self.network = config["network"]

    @classmethod
    def load_config_or_defaults(cls, config_path=None):
        if config_path is None:
            # Consider following complete LND default for convention (https://git.io/J3jMj)
            config_path = "~/.lnd/lnd.conf"

        config_path = _resolve_path(config_path)
        parser = configparser.ConfigParser()
        if len(parser.read(config_path)) == 0:
            log.debug(
                f"No valid config file found at {config_path}, using overrides or "
                + "defaults."
            )
            config = DEFAULTS.copy()
            return config

        config = {}
        config["rpchost"] = parser.get(
            "Application Options", "rpclisten", fallback=DEFAULTS["rpchost"]
        )

        config["tlscertpath"] = parser.get(
            "Application Options", "tlscertpath", fallback=DEFAULTS["tlscertpath"]
        )
        config["adminmacaroonpath"] = parser.get(
            "Application Options",
            "adminmacaroonpath",
            fallback=DEFAULTS["adminmacaroonpath"],
        )

        network = "testnet"
        if parser.getboolean("Bitcoin", "bitcoin.mainnet", fallback=False):
            network = "mainnet"
        elif parser.getboolean("Bitcoin", "bitcoin.testnet", fallback=False):
            network = "testnet"
        elif parser.getboolean("Bitcoin", "bitcoin.simnet", fallback=False):
            network = "simnet"
        elif parser.getboolean("Bitcoin", "bitcoin.regtest", fallback=False):
            network = "regtest"

        config["network"] = network

        return config
