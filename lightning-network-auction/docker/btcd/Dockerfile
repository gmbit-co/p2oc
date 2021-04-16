FROM golang:1.15-alpine3.13 as builder

# Install build dependencies such as git and glide.
RUN apk add --no-cache git

WORKDIR $GOPATH/src/github.com/btcsuite/btcd

ARG BTCD_VERSION=v0.21.0-beta

# Grab and install the latest version of of btcd and all related dependencies.
RUN git clone https://github.com/btcsuite/btcd.git . \
    && git checkout $BTCD_VERSION \
    &&  GO111MODULE=on go install -v . ./cmd/...

# Start a new image
FROM alpine:3.13 as final

COPY --from=builder /go/bin /bin

ENTRYPOINT ["btcd"]
