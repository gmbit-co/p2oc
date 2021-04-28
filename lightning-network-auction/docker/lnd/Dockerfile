FROM golang:1.15-alpine3.13 as builder

# Install build dependencies
RUN apk add --no-cache --update alpine-sdk \
    git \
    make

WORKDIR $GOPATH/src/github.com/lightningnetwork/lnd

ARG LND_VERSION=regata/signpbst

# Grab and install the latest version of of btcwallet and all related dependencies.
RUN git clone https://github.com/flywheelstudio/lnd.git . \
    && git checkout $LND_VERSION \
    &&  make release-install

# Start a new image
FROM alpine:3.13 as final

COPY --from=builder /go/bin /bin

# Expose lnd ports (p2p, rpc).
EXPOSE 9735 10009

ENTRYPOINT ["lnd"]
