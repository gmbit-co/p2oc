import os
import codecs
import grpc

from lnrpc import rpc_pb2 as lnmsg
from lnrpc import rpc_pb2_grpc as lnrpc
from lnrpc.walletrpc import walletkit_pb2_grpc as walletrpc, walletkit_pb2 as walletmsg

from lnrpc.signrpc import signer_pb2_grpc as signrpc, signer_pb2 as signmsg
from lnrpc.routerrpc import router_pb2_grpc as routerrpc, router_pb2 as routermsg


class LndRpc:
    def __init__(self, rpchost, tlscertpath, adminmacaroonpath):
        os.environ["GRPC_SSL_CIPHER_SUITES"] = "HIGH+ECDSA"

        with open(tlscertpath, "rb") as f:
            cert = f.read()
        cert_creds = grpc.ssl_channel_credentials(cert)

        with open(adminmacaroonpath, "rb") as f:
            macaroon = f.read()
            macaroon = codecs.encode(macaroon, "hex")

        # for more info see grpc docs
        metadata_callback = lambda ctx, callback: callback(
            [("macaroon", macaroon)], None
        )

        # now build meta data credentials
        auth_creds = grpc.metadata_call_credentials(metadata_callback)

        # combine the cert credentials and the macaroon auth credentials
        # such that every call is properly encrypted and authenticated
        combined_creds = grpc.composite_channel_credentials(cert_creds, auth_creds)

        channel = grpc.secure_channel(rpchost, combined_creds)
        self.rpchost = rpchost
        self.lnd = lnrpc.LightningStub(channel)
        self.wallet = walletrpc.WalletKitStub(channel)
        self.router = routerrpc.RouterStub(channel)
        self.signer = signrpc.SignerStub(channel)
