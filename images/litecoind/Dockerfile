# Litecoin Core from the official release tarball, checksum-verified.
# Build: docker build --build-arg VERSION=0.21.4 --build-arg SHA256=<sum> -t litecoind .
FROM debian:bookworm-slim AS fetch
ARG VERSION
ARG SHA256
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl && rm -rf /var/lib/apt/lists/*
WORKDIR /tmp
RUN curl -fsSLO "https://download.litecoin.org/litecoin-${VERSION}/linux/litecoin-${VERSION}-x86_64-linux-gnu.tar.gz" \
 && echo "${SHA256}  litecoin-${VERSION}-x86_64-linux-gnu.tar.gz" | sha256sum -c - \
 && tar -xzf "litecoin-${VERSION}-x86_64-linux-gnu.tar.gz" \
 && install -m 0755 "litecoin-${VERSION}/bin/litecoind" "litecoin-${VERSION}/bin/litecoin-cli" /usr/local/bin/

FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates && rm -rf /var/lib/apt/lists/* \
 && useradd -u 1000 -m -d /data litecoin
COPY --from=fetch /usr/local/bin/litecoind /usr/local/bin/litecoin-cli /usr/local/bin/
USER litecoin
WORKDIR /data
VOLUME ["/data/.litecoin"]
EXPOSE 9332 9333 28432 28433
ENTRYPOINT ["litecoind"]
