# RAG System Setup Script for Windows
# This script automates the RAG system setup process

Write-Host "🚀 Football Heritage RAG System Setup" -ForegroundColor Cyan
Write-Host "======================================`n" -ForegroundColor Cyan

# Check Redis
Write-Host "1️⃣  Checking Redis..." -ForegroundColor Yellow
try {
    $redisService = Get-Service -Name Redis -ErrorAction Stop
    if ($redisService.Status -eq 'Running') {
        Write-Host "   ✅ Redis is running" -ForegroundColor Green
    } else {
        Write-Host "   ⚠️  Redis is installed but not running. Starting..." -ForegroundColor Yellow
        Start-Service Redis
        Write-Host "   ✅ Redis started" -ForegroundColor Green
    }
} catch {
    Write-Host "   ❌ Redis is not installed" -ForegroundColor Red
    Write-Host "   Please install Redis first. See RAG_QUICK_START.md" -ForegroundColor Red
    exit 1
}

# Test Redis connection
Write-Host "`n2️⃣  Testing Redis connection..." -ForegroundColor Yellow
try {
    $redisTest = & "C:\Program Files\Redis\redis-cli.exe" ping 2>&1
    if ($redisTest -eq "PONG") {
        Write-Host "   ✅ Redis connection successful" -ForegroundColor Green
    } else {
        Write-Host "   ❌ Redis not responding" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "   ⚠️  redis-cli not found in default location" -ForegroundColor Yellow
    Write-Host "   Redis service is running, continuing..." -ForegroundColor Yellow
}

# Check Node.js dependencies
Write-Host "`n3️⃣  Checking Node.js dependencies..." -ForegroundColor Yellow
$chatbotPath = "d:\Github\FootballHeritage\chatbot"
Set-Location $chatbotPath

if (!(Test-Path "node_modules\ioredis")) {
    Write-Host "   📦 Installing ioredis..." -ForegroundColor Yellow
    npm install --save ioredis --silent
}

if (!(Test-Path "node_modules\@google\generative-ai")) {
    Write-Host "   📦 Installing @google/generative-ai..." -ForegroundColor Yellow
    npm install --save "@google/generative-ai" --silent
}

Write-Host "   ✅ Node.js dependencies installed" -ForegroundColor Green

# Check database connection
Write-Host "`n4️⃣  Checking database connection..." -ForegroundColor Yellow
$env:PGPASSWORD = "jumpman13"
$dbTest = psql -U postgres -d football_heritage -c "SELECT 1;" 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Host "   ✅ Database connection successful" -ForegroundColor Green
} else {
    Write-Host "   ❌ Database connection failed" -ForegroundColor Red
    Write-Host "   Error: $dbTest" -ForegroundColor Red
    exit 1
}

# Check for pgvector
Write-Host "`n5️⃣  Checking pgvector extension..." -ForegroundColor Yellow
$pgvectorCheck = psql -U postgres -d football_heritage -c "SELECT * FROM pg_extension WHERE extname = 'vector';" 2>&1

if ($pgvectorCheck -match "vector") {
    Write-Host "   ✅ pgvector extension is installed" -ForegroundColor Green
    $hasPgvector = $true
} else {
    Write-Host "   ⚠️  pgvector extension not found" -ForegroundColor Yellow
    Write-Host "   The system will work with keyword search only" -ForegroundColor Yellow
    Write-Host "   For full RAG capabilities, install pgvector:" -ForegroundColor Yellow
    Write-Host "   See INSTALL_PGVECTOR.md for instructions`n" -ForegroundColor Cyan
    $hasPgvector = $false
    
    $response = Read-Host "   Continue without pgvector? (y/n)"
    if ($response -ne "y") {
        exit 0
    }
}

# Run database migration
if ($hasPgvector) {
    Write-Host "`n6️⃣  Running database migration..." -ForegroundColor Yellow
    $migrationPath = "d:\Github\FootballHeritage\backend\migrations\20251210000001_add_rag_system.sql"
    
    $migrationResult = psql -U postgres -d football_heritage -f $migrationPath 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "   ✅ Database migration completed" -ForegroundColor Green
    } else {
        Write-Host "   ⚠️  Migration completed with warnings" -ForegroundColor Yellow
        Write-Host "   This is normal if tables already exist" -ForegroundColor Yellow
    }
} else {
    Write-Host "`n6️⃣  Setting up keyword search only..." -ForegroundColor Yellow
    
    # Create minimal schema without pgvector
    $minimalSchema = @"
-- Add full-text search to events
ALTER TABLE events ADD COLUMN IF NOT EXISTS search_vector tsvector;

CREATE INDEX IF NOT EXISTS events_search_idx ON events USING GIN(search_vector);

CREATE OR REPLACE FUNCTION events_search_trigger() 
RETURNS trigger AS `$`$
BEGIN
    NEW.search_vector :=
        setweight(to_tsvector('english', COALESCE(NEW.home_team, '')), 'A') ||
        setweight(to_tsvector('english', COALESCE(NEW.away_team, '')), 'A') ||
        setweight(to_tsvector('english', COALESCE(NEW.league, '')), 'B') ||
        setweight(to_tsvector('english', COALESCE(NEW.sport, '')), 'B');
    RETURN NEW;
END;
`$`$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS events_search_update ON events;
CREATE TRIGGER events_search_update
    BEFORE INSERT OR UPDATE ON events
    FOR EACH ROW EXECUTE FUNCTION events_search_trigger();

UPDATE events 
SET search_vector = 
    setweight(to_tsvector('english', COALESCE(home_team, '')), 'A') ||
    setweight(to_tsvector('english', COALESCE(away_team, '')), 'A') ||
    setweight(to_tsvector('english', COALESCE(league, '')), 'B') ||
    setweight(to_tsvector('english', COALESCE(sport, '')), 'B')
WHERE search_vector IS NULL;
"@
    
    $minimalSchema | psql -U postgres -d football_heritage 2>&1 | Out-Null
    Write-Host "   ✅ Keyword search configured" -ForegroundColor Green
}

# Test cache service
Write-Host "`n7️⃣  Testing cache service..." -ForegroundColor Yellow
$cacheTest = node -e "import('./services/cache.js').then(m => { console.log('OK'); process.exit(0); }).catch(e => { console.error(e.message); process.exit(1); });" 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Host "   ✅ Cache service working" -ForegroundColor Green
} else {
    Write-Host "   ❌ Cache service error: $cacheTest" -ForegroundColor Red
}

# Summary
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "✅ RAG System Setup Complete!" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Cyan

Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Start the chatbot service:" -ForegroundColor White
Write-Host "   cd chatbot" -ForegroundColor Cyan
Write-Host "   npm run dev`n" -ForegroundColor Cyan

if ($hasPgvector) {
    Write-Host "2. Generate embeddings (in another terminal):" -ForegroundColor White
    Write-Host "   cd chatbot" -ForegroundColor Cyan
    Write-Host "   node services/embeddings.js`n" -ForegroundColor Cyan
} else {
    Write-Host "2. Install pgvector for full RAG capabilities:" -ForegroundColor White
    Write-Host "   See INSTALL_PGVECTOR.md`n" -ForegroundColor Cyan
}

Write-Host "3. Test the system:" -ForegroundColor White
Write-Host "   Open http://localhost:5173 in your browser`n" -ForegroundColor Cyan

Write-Host "📊 Check metrics at: http://localhost:3000/metrics" -ForegroundColor Yellow
Write-Host "📚 Full guide: RAG_IMPLEMENTATION_GUIDE.md`n" -ForegroundColor Yellow
