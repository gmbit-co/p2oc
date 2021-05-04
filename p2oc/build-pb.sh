export LND_VERSION=regata/signpbst

echo "Downloading source..."

cd /src
git clone https://github.com/googleapis/googleapis.git

git clone https://github.com/flywheelstudio/lnd.git
cd lnd
git checkout $LND_VERSION

mkdir -p /src/p2oc/lnrpc
cd /src/p2oc/lnrpc

echo "Compiling grpc protobufs..."

python -m grpc_tools.protoc \
    --proto_path=/src/googleapis \
    --proto_path=/src/lnd/lnrpc \
    --python_out=. \
    --grpc_python_out=. \
    $(find /src/lnd/lnrpc/ -iname "*.proto")

echo "Cleaning-up..."

cd /src
rm -rf ./googleapis
rm -rf ./lnd
