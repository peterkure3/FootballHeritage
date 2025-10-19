#!/bin/bash

# Football Heritage Backend - Development Setup Script
# This script sets up the local development environment

set -e  # Exit on error

echo "🏈 Football Heritage Backend - Development Setup"
echo "================================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if Rust is installed
if ! command -v cargo &> /dev/null; then
    echo -e "${RED}❌ Rust is not installed${NC}"
    echo "Please install Rust from https://rustup.rs/"
    exit 1
fi
echo -e "${GREEN}✓ Rust is installed${NC}"

# Check if PostgreSQL is installed
if ! command -v psql &> /dev/null; then
    echo -e "${YELLOW}⚠️  PostgreSQL client not found${NC}"
    echo "Please ensure PostgreSQL is installed and accessible"
else
    echo -e "${GREEN}✓ PostgreSQL client found${NC}"
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  .env file not found, creating from .env.example${NC}"
    cp .env.example .env
    echo -e "${GREEN}✓ Created .env file${NC}"
    echo ""
    echo -e "${YELLOW}⚠️  IMPORTANT: Please edit .env and configure:${NC}"
    echo "   - DATABASE_URL (PostgreSQL connection string)"
    echo "   - JWT_SECRET (256-bit random secret)"
    echo "   - ENCRYPTION_KEY (32-byte random key)"
    echo ""
else
    echo -e "${GREEN}✓ .env file exists${NC}"
fi

# Generate secure keys if needed
echo ""
echo "🔐 Security Keys Setup"
echo "====================="

# Check if openssl is available for key generation
if command -v openssl &> /dev/null; then
    echo -e "${GREEN}✓ OpenSSL found, can generate secure keys${NC}"

    # Check if JWT_SECRET needs generation
    if grep -q "your-super-secure-jwt-secret-key-here" .env 2>/dev/null; then
        echo ""
        echo "Generating JWT_SECRET..."
        JWT_SECRET=$(openssl rand -base64 64 | tr -d '\n')
        sed -i.bak "s|JWT_SECRET=.*|JWT_SECRET=${JWT_SECRET}|" .env
        echo -e "${GREEN}✓ Generated JWT_SECRET${NC}"
    fi

    # Check if ENCRYPTION_KEY needs generation
    if grep -q "your-256-bit-encryption-key-for-wallet-balances-here" .env 2>/dev/null; then
        echo "Generating ENCRYPTION_KEY..."
        ENCRYPTION_KEY=$(openssl rand -base64 32 | tr -d '\n')
        sed -i.bak "s|ENCRYPTION_KEY=.*|ENCRYPTION_KEY=${ENCRYPTION_KEY}|" .env
        echo -e "${GREEN}✓ Generated ENCRYPTION_KEY${NC}"
    fi

    rm -f .env.bak
else
    echo -e "${YELLOW}⚠️  OpenSSL not found. Please manually generate secure keys:${NC}"
    echo "   JWT_SECRET: 64+ character random string"
    echo "   ENCRYPTION_KEY: 32-byte (44 characters base64) random string"
fi

# Create necessary directories
echo ""
echo "📁 Creating directories..."
mkdir -p logs
mkdir -p certs
mkdir -p data
echo -e "${GREEN}✓ Created directories${NC}"

# Check database configuration
echo ""
echo "🗄️  Database Setup"
echo "================="

if grep -q "postgresql://username:password@localhost" .env 2>/dev/null; then
    echo -e "${YELLOW}⚠️  Database URL is using example credentials${NC}"
    echo "Please update DATABASE_URL in .env with your PostgreSQL credentials"
    echo ""
    echo "Default format:"
    echo "DATABASE_URL=postgresql://username:password@localhost:5432/football_heritage_betting"
    echo ""
    DB_CONFIGURED=false
else
    echo -e "${GREEN}✓ Database URL is configured${NC}"
    DB_CONFIGURED=true
fi

# Try to create database if configured
if [ "$DB_CONFIGURED" = true ]; then
    echo ""
    read -p "Would you like to create the database and run migrations? (y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # Extract database info from DATABASE_URL
        DB_URL=$(grep DATABASE_URL .env | cut -d '=' -f2)

        echo "Creating database..."
        # This will create the database if it doesn't exist
        psql "$DB_URL" -c "SELECT 1;" 2>/dev/null || {
            echo "Creating database football_heritage_betting..."
            # Extract connection params
            createdb football_heritage_betting 2>/dev/null && echo -e "${GREEN}✓ Database created${NC}" || echo -e "${YELLOW}⚠️  Database might already exist${NC}"
        }

        echo ""
        echo "Running database schema..."
        if [ -f schema.sql ]; then
            psql "$DB_URL" < schema.sql && echo -e "${GREEN}✓ Schema applied${NC}"
        else
            echo -e "${YELLOW}⚠️  schema.sql not found${NC}"
        fi

        echo ""
        echo "Running SQLx migrations..."
        cargo install sqlx-cli --no-default-features --features postgres 2>/dev/null || true
        sqlx migrate run && echo -e "${GREEN}✓ Migrations applied${NC}" || echo -e "${YELLOW}⚠️  Migrations failed or already applied${NC}"
    fi
fi

# Install development dependencies
echo ""
echo "📦 Installing dependencies..."
cargo build
echo -e "${GREEN}✓ Dependencies installed${NC}"

# Generate self-signed certificates for development (if OpenSSL is available)
if command -v openssl &> /dev/null; then
    if [ ! -f certs/server.crt ] || [ ! -f certs/server.key ]; then
        echo ""
        read -p "Generate self-signed TLS certificates for development? (y/n) " -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo "Generating self-signed certificate..."
            openssl req -x509 -newkey rsa:4096 -nodes \
                -keyout certs/server.key \
                -out certs/server.crt \
                -days 365 \
                -subj "/C=US/ST=State/L=City/O=FootballHeritage/CN=localhost"
            echo -e "${GREEN}✓ Self-signed certificate generated${NC}"
            echo -e "${YELLOW}⚠️  This is for development only. Use proper certificates in production!${NC}"
        fi
    else
        echo -e "${GREEN}✓ TLS certificates already exist${NC}"
    fi
fi

# Final summary
echo ""
echo "================================================"
echo -e "${GREEN}✅ Setup Complete!${NC}"
echo "================================================"
echo ""
echo "📋 Next Steps:"
echo ""
echo "1. Review and update .env with your configuration"
echo "   - Verify DATABASE_URL is correct"
echo "   - Ensure JWT_SECRET and ENCRYPTION_KEY are set"
echo ""
echo "2. Start the development server:"
echo "   cargo run"
echo ""
echo "3. Run tests:"
echo "   cargo test"
echo ""
echo "4. Run with hot reload (install cargo-watch):"
echo "   cargo install cargo-watch"
echo "   cargo watch -x run"
echo ""
echo "5. Check API documentation:"
echo "   See BETTING_SERVICE_GUIDE.md"
echo "   See SIMPLIFIED_BETTING_README.md"
echo ""
echo "🔗 Useful Commands:"
echo "   cargo check          - Quick compile check"
echo "   cargo test          - Run tests"
echo "   cargo build         - Build project"
echo "   cargo run           - Run server"
echo "   cargo clippy        - Linter"
echo "   cargo fmt           - Format code"
echo ""
echo "📚 Documentation:"
echo "   - BETTING_SERVICE_GUIDE.md - Complete API guide"
echo "   - TRANSACTION_FIXES.md - Technical details"
echo "   - DEPLOYMENT_CHECKLIST.md - Production deployment"
echo "   - QUICK_REFERENCE.md - Quick reference card"
echo ""
echo -e "${GREEN}Happy coding! 🚀${NC}"
echo ""
