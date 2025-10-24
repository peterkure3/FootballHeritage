# Generate bcrypt hash for admin password
# This calls the backend's register endpoint to generate a proper hash

Write-Host "Generating bcrypt hash for admin password..." -ForegroundColor Cyan
Write-Host ""

$password = "Admin123!"

# Create a temporary user to get the hash format
$body = @{
    email = "temp_hash_gen@test.com"
    password = $password
    first_name = "Test"
    last_name = "User"
    date_of_birth = "1990-01-01"
} | ConvertTo-Json

Write-Host "Password to hash: $password" -ForegroundColor Yellow
Write-Host ""
Write-Host "To get the bcrypt hash, you can:" -ForegroundColor Green
Write-Host "1. Register a test user with password 'Admin123!'" -ForegroundColor White
Write-Host "2. Query the database: SELECT password_hash FROM users WHERE email = 'test@test.com'" -ForegroundColor White
Write-Host "3. Copy that hash into the migration file" -ForegroundColor White
Write-Host ""
Write-Host "OR use this online tool:" -ForegroundColor Green
Write-Host "https://bcrypt-generator.com/" -ForegroundColor Cyan
Write-Host "- Enter password: Admin123!" -ForegroundColor White
Write-Host "- Rounds: 12" -ForegroundColor White
Write-Host "- Copy the generated hash" -ForegroundColor White
