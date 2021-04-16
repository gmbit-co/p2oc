

btcwallet --simnet \
    --appdata=/data \
    --cafile=/btcd-rpc/rpc.cert \
    --rpcconnect=btcd:${BTCD_RPCPORT} \
    --username=${BTCD_RPCUSER} \
    --password=${BTCD_RPCPASS} \
    --createtemp
