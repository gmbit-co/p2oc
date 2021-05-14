import tempfile
from pathlib import Path

from p2oc.config import Config


def test_config():
    rpchost = "lnd:10009"
    override_rpchost = "lnd2:10009"
    tlscertpath = "/root/src/umbrel/lnd/tls.cert"
    adminmacaroonpath = "/root/src/umbrel/lnd/data/chain/bitcoin/testnet/admin.macaroon"

    with tempfile.TemporaryDirectory() as temp_dir:
        config_path = Path(temp_dir) / "lnd.conf"
        with open(config_path, "wt") as f:
            f.write(
                f"""
[Application Options]
# LND host
rpclisten={rpchost}
tlscertpath={tlscertpath}
adminmacaroonpath={adminmacaroonpath}

[Bitcoin]
bitcoin.testnet=1
"""
            )
        config = Config(config_path)
        assert config.rpchost == rpchost
        assert config.tlscertpath == tlscertpath
        assert config.adminmacaroonpath == adminmacaroonpath

        # Test override
        config = Config(config_path, config_overrides={"rpchost": override_rpchost})
        assert config.rpchost == override_rpchost
