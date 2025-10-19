@echo off
set DATABASE_URL=postgresql://postgres:jumpman13@localhost:5432/football_heritage
set JWT_SECRET=your-super-secret-jwt-key-min-32-chars-long-please
set ENCRYPTION_KEY=12345678901234567890123456789012
set HTTPS_ENABLED=false
echo Starting application...
timeout /t 2 >nul
target\release\football-heritage-backend.exe
