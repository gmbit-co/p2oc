import codecs
import os
import grpc

import rpc_pb2 as lnmsg
import rpc_pb2_grpc as lnrpc
from walletrpc import walletkit_pb2_grpc as walletrpc, walletkit_pb2 as walletmsg
from signrpc import signer_pb2_grpc as signrpc, signer_pb2 as signmsg

class LndRpc:
    def __init__(self, host, cert_path, macaroon_path):
        os.environ["GRPC_SSL_CIPHER_SUITES"] = 'HIGH+ECDSA'

        with open(cert_path, 'rb') as f:
            cert = f.read()
        cert_creds = grpc.ssl_channel_credentials(cert)
        
        with open(os.path.expanduser(macaroon_path), 'rb') as f:
            macaroon = f.read()
            macaroon = codecs.encode(macaroon, 'hex')
        
        # for more info see grpc docs
        metadata_callback = lambda context, callback: callback([('macaroon', macaroon)], None)
        
        # now build meta data credentials
        auth_creds = grpc.metadata_call_credentials(metadata_callback)

        # combine the cert credentials and the macaroon auth credentials
        # such that every call is properly encrypted and authenticated
        combined_creds = grpc.composite_channel_credentials(cert_creds, auth_creds)

        channel = grpc.secure_channel(host, combined_creds)
        self.lnd = lnrpc.LightningStub(channel)
        self.wallet = walletrpc.WalletKitStub(channel)
