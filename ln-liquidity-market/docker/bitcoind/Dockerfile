# Just a dockerfile with some defaults
FROM ruimarinho/bitcoin-core:0.20-alpine

ENTRYPOINT [ \
    "btcd", \
    "-chain=${BTCD_NETWORK}", \
    "-debug", \
    "-datadir=/bitcoin/.bitcoin", \
    "-rpcuser=${BTCD_RPCUSER}", \
    "-rpcpassword=${BTCD_RPCPASS}", \
    "-rpcport=${BTCD_RPCPORT}", \
    "-rpcbind=0.0.0.0:${BTCD_RPCPORT}", \
    "-rpcallowip=0.0.0.0/0", \
    "-listenonion=0", \
    "-printtoconsole", \
    "-server", \
    "-txindex" \
]
