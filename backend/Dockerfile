FROM rust:1.90-bookworm AS build
WORKDIR /app
COPY . .
ENV SQLX_OFFLINE=true
# Portable baseline; local Cargo config uses host-specific CPU instructions.
ENV RUSTFLAGS="-C target-cpu=x86-64"
ENV CARGO_BUILD_JOBS=2 CARGO_TARGET_DIR=/app/target
RUN --mount=type=cache,target=/usr/local/cargo/registry \
    --mount=type=cache,target=/app/target \
    cargo --version && rustc --version \
    && cargo build --locked --release --bin football-heritage-backend --bin migrate \
    && cp /app/target/release/football-heritage-backend /app/server \
    && cp /app/target/release/migrate /app/migrate

FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl \
    && rm -rf /var/lib/apt/lists/* && useradd --system --uid 10001 app
WORKDIR /app
COPY --from=build /app/server /app/server
COPY --from=build /app/migrate /app/migrate
USER 10001
ENV HOST=0.0.0.0 PORT=8888 HTTPS_ENABLED=false APP_ENV=production
EXPOSE 8888
CMD ["/app/server"]
