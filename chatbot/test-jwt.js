/**
 * Quick JWT Test Script
 * Tests if JWT secret is correctly configured
 */

import jwt from 'jsonwebtoken';
import dotenv from 'dotenv';

dotenv.config();

console.log('🔐 Testing JWT Configuration\n');

// Test token generation
const testPayload = {
    sub: 'test-user-id-123',
    email: 'test@example.com',
    iat: Math.floor(Date.now() / 1000),
    exp: Math.floor(Date.now() / 1000) + (60 * 60), // 1 hour
};

try {
    // Generate token
    const token = jwt.sign(testPayload, process.env.JWT_SECRET);
    console.log('✅ Token generated successfully');
    console.log(`Token: ${token.substring(0, 50)}...`);
    
    // Verify token
    const decoded = jwt.verify(token, process.env.JWT_SECRET);
    console.log('\n✅ Token verified successfully');
    console.log('Decoded payload:', {
        sub: decoded.sub,
        email: decoded.email,
    });
    
    console.log('\n✅ JWT configuration is correct!');
    console.log(`JWT Secret length: ${process.env.JWT_SECRET.length} characters`);
    
} catch (error) {
    console.error('\n❌ JWT test failed:', error.message);
    console.error('\nPlease check:');
    console.error('1. JWT_SECRET in .env matches backend');
    console.error('2. JWT_SECRET is at least 32 characters');
    process.exit(1);
}
