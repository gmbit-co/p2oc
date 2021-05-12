FROM golang:1.15-alpine3.13 as builder

# Install build dependencies such as git and glide.
RUN apk add --no-cache git

WORKDIR $GOPATH/src/github.com/btcsuite/btcwallet

ARG BTCWALLET_VERSION=walletdb/v1.3.4 

# Grab and install the latest version of of btcwallet and all related dependencies.
RUN git clone https://github.com/btcsuite/btcwallet.git . \
    && git checkout $BTCWALLET_VERSION \
    &&  GO111MODULE=on go install -v . ./cmd/...

# Start a new image
FROM alpine:3.13 as final

COPY --from=builder /go/bin /bin

ENTRYPOINT ["btcwallet"]
