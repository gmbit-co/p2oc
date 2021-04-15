FROM golang:1.15.7-alpine as builder

LABEL maintainer="Julian Villella <julian@flystud.io>"

# Install build dependencies such as git and glide.
RUN apk add --no-cache git gcc musl-dev

WORKDIR $GOPATH/src/github.com/btcsuite/btcwallet

# Pin down btcd to a version that we know works with lnd.
ARG BTCWALLET_VERSION=v0.11.0

# Grab and install the latest version of of btcd and all related dependencies.
RUN git clone https://github.com/btcsuite/btcwallet.git . \
    && git checkout $BTCWALLET_VERSION \
    && GO111MODULE=on go install -v . ./cmd/...

# Start a new image
FROM alpine as final

# Expose mainnet ports (rpc)
EXPOSE 8332

# Expose testnet ports (rpc)
EXPOSE 18332

# Expose simnet ports (rpc)
EXPOSE 18554

# Copy the compiled binaries from the builder image.
COPY --from=builder /go/bin/btcwallet /bin/

COPY "start-btcwallet.sh" .

RUN apk add --no-cache bash && chmod +x start-btcwallet.sh

# Create a volume to house pregenerated RPC credentials. This will be
# shared with any lnd, btcctl containers so they can securely query btcd's RPC
# server.
# You should NOT do this before certificate generation!
# Otherwise manually generated certificate will be overridden with shared
# mounted volume! For more info read dockerfile "VOLUME" documentation.
VOLUME ["/rpc"]
