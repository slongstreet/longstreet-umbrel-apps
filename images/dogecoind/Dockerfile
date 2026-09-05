# Dogecoin Core from the official GitHub release tarball, checksum-verified.
# Build: docker build --build-arg VERSION=1.14.9 --build-arg SHA256=<sum> -t dogecoind .
FROM debian:bookworm-slim AS fetch
ARG VERSION
ARG SHA256
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl && rm -rf /var/lib/apt/lists/*
WORKDIR /tmp
RUN curl -fsSLO "https://github.com/dogecoin/dogecoin/releases/download/v${VERSION}/dogecoin-${VERSION}-x86_64-linux-gnu.tar.gz" \
 && echo "${SHA256}  dogecoin-${VERSION}-x86_64-linux-gnu.tar.gz" | sha256sum -c - \
 && tar -xzf "dogecoin-${VERSION}-x86_64-linux-gnu.tar.gz" \
 && install -m 0755 "dogecoin-${VERSION}/bin/dogecoind" "dogecoin-${VERSION}/bin/dogecoin-cli" /usr/local/bin/

FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates && rm -rf /var/lib/apt/lists/* \
 && useradd -u 1000 -m -d /data dogecoin
COPY --from=fetch /usr/local/bin/dogecoind /usr/local/bin/dogecoin-cli /usr/local/bin/
USER dogecoin
WORKDIR /data
VOLUME ["/data/.dogecoin"]
EXPOSE 22555 22556 28434 28435
ENTRYPOINT ["dogecoind"]
