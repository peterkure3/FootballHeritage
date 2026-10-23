FROM rust:1.90-bookworm AS build
WORKDIR /app
COPY . .
ENV SQLX_OFFLINE=true
# Portable baseline; local Cargo config uses host-specific CPU instructions.
ENV RUSTFLAGS="-C target-cpu=x86-64"
RUN cargo build --locked --release --bin football-heritage-backend

FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/* && useradd --system --uid 10001 app
WORKDIR /app
COPY --from=build /app/target/release/football-heritage-backend /app/server
USER 10001
ENV HOST=0.0.0.0 PORT=8888 HTTPS_ENABLED=false APP_ENV=production
EXPOSE 8888
CMD ["/app/server"]
