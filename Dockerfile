# ---- Stage 1: Rust build ----
FROM rust:1.82-bookworm AS rust-builder
WORKDIR /build
COPY Cargo.toml Cargo.lock rust-toolchain.toml ./
COPY crates/ crates/
RUN cargo build --release

# ---- Stage 2: Frontend build ----
FROM node:22-alpine AS frontend-builder
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

# ---- Stage 3: Python runtime ----
FROM python:3.11-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install maturin for building the Rust extension
RUN pip install --no-cache-dir maturin>=1.7

# Copy Rust build artifacts
COPY --from=rust-builder /build/target/release/lib_engine.so /tmp/engine.so

# Copy Python source and config
COPY pyproject.toml Cargo.toml Cargo.lock rust-toolchain.toml ./
COPY crates/ crates/
COPY src/ src/

# Build and install the Python package with Rust extension
RUN maturin build --release --out dist && \
    pip install --no-cache-dir dist/*.whl && \
    rm -rf dist

# Copy frontend build output
COPY --from=frontend-builder /build/dist /app/static

# Copy data and config files
COPY data/ data/
COPY alembic.ini alembic/
COPY alembic/ alembic/

EXPOSE 8000

CMD ["uvicorn", "biolab.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
