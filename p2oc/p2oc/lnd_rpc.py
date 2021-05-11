import os
import codecs
import grpc
import logging
from pathlib import Path

from lnrpc import rpc_pb2 as lnmsg
from lnrpc import rpc_pb2_grpc as lnrpc
from lnrpc.walletrpc import walletkit_pb2_grpc as walletrpc, walletkit_pb2 as walletmsg
import configparser

from lnrpc.signrpc import signer_pb2_grpc as signrpc, signer_pb2 as signmsg
from lnrpc.routerrpc import router_pb2_grpc as routerrpc, router_pb2 as routermsg

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(f"lnd_rpc.py - pid({os.getpid()})")


def _resolve_path(path):
    path = os.path.expanduser(path)
    return str(Path(path).resolve())


class LndRpc:
    def __init__(self, config_path=None, config_overrides={}):
        config = LndRpc.load_config(config_path)
        config.update(config_overrides)

        os.environ["GRPC_SSL_CIPHER_SUITES"] = "HIGH+ECDSA"

        with open(_resolve_path(config["tlscertpath"]), "rb") as f:
            cert = f.read()
        cert_creds = grpc.ssl_channel_credentials(cert)

        with open(_resolve_path(config["adminmacaroonpath"]), "rb") as f:
            macaroon = f.read()
            macaroon = codecs.encode(macaroon, "hex")

        # for more info see grpc docs
        metadata_callback = lambda context, callback: callback(
            [("macaroon", macaroon)], None
        )

        # now build meta data credentials
        auth_creds = grpc.metadata_call_credentials(metadata_callback)

        # combine the cert credentials and the macaroon auth credentials
        # such that every call is properly encrypted and authenticated
        combined_creds = grpc.composite_channel_credentials(cert_creds, auth_creds)

        channel = grpc.secure_channel(config["host"], combined_creds)
        self.host = config["host"]
        self.lnd = lnrpc.LightningStub(channel)
        self.wallet = walletrpc.WalletKitStub(channel)
        self.router = routerrpc.RouterStub(channel)
        self.signer = signrpc.SignerStub(channel)
        self.config = config

    @classmethod
    def load_config(cls, config_path=None):
        if config_path is None:
            # Consider following complete LND default fir convention (https://git.io/J3jMj)
            config_path = "~/.lnd/lnd.conf"

        config_path = _resolve_path(config_path)

        parser = configparser.ConfigParser()
        if len(parser.read(config_path)) == 0:
            log.info(
                f"No valid config file found at {config_path}, using overrides or "
                + "defaults."
            )

        config = {}
        config["host"] = parser.get(
            "Application Options", "rpclisten", fallback="localhost:10009"
        )

        config["tlscertpath"] = parser.get(
            "Application Options", "tlscertpath", fallback="~/.lnd/tls.cert"
        )
        config["tlscertpath"] = _resolve_path(config["tlscertpath"])

        config["adminmacaroonpath"] = parser.get(
            "Application Options",
            "adminmacaroonpath",
            fallback="~/.lnd/data/chain/bitcoin/testnet/admin.macaroon",
        )
        config["adminmacaroonpath"] = _resolve_path(config["adminmacaroonpath"])

        network = "testnet"
        if parser.get("Bitcoin", "bitcoin.mainnet", fallback="false") == "true":
            network = "mainnet"
        elif parser.get("Bitcoin", "bitcoin.testnet", fallback="false") == "true":
            network = "testnet"
        elif parser.get("Bitcoin", "bitcoin.simnet", fallback="false") == "true":
            network = "simnet"
        elif parser.get("Bitcoin", "bitcoin.regtest", fallback="false") == "true":
            network = "regtest"

        config["network"] = network

        return config
