# Football Heritage Betting API Documentation

## Base URL

```
Development: http://localhost:8080
Production: https://yourdomain.com
```

All API endpoints are prefixed with `/api/v1` unless otherwise noted.

---

## Table of Contents

1. [Authentication](#authentication)
2. [Wallet Management](#wallet-management)
3. [Betting](#betting)
4. [Responsible Gambling Limits](#responsible-gambling-limits)
5. [User Profile](#user-profile)
6. [System](#system)
7. [Error Responses](#error-responses)
8. [Rate Limits](#rate-limits)

---

## Authentication

### Register New User

Create a new user account.

**Endpoint:** `POST /api/v1/auth/register`

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "first_name": "John",
  "last_name": "Doe",
  "date_of_birth": "1990-01-01",
  "phone": "+1234567890",
  "address": "123 Main St, City, State 12345"
}
```

**Validation Rules:**
- Email: Valid email format
- Password: Min 8 characters, contains uppercase, lowercase, number, special character
- Age: Must be 21+ years old
- Phone: Valid phone number format
- All fields required

**Success Response:** `201 Created`
```json
{
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "created_at": "2024-10-19T12:00:00Z"
  },
  "token": "jwt_token_here"
}
```

**Error Responses:**
- `400 Bad Request` - Validation failed
- `409 Conflict` - Email already exists
- `403 Forbidden` - Under 21 years old

---

### Login

Authenticate and receive JWT token.

**Endpoint:** `POST /api/v1/auth/login`

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```

**Success Response:** `200 OK`
```json
{
  "token": "jwt_token_here",
  "expires_at": "2024-10-20T12:00:00Z",
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe"
  }
}
```

**Error Responses:**
- `401 Unauthorized` - Invalid credentials
- `423 Locked` - Account locked due to failed login attempts
- `429 Too Many Requests` - Rate limit exceeded

**Rate Limit:** 10 requests per minute per IP

---

### Logout

Invalidate current session.

**Endpoint:** `POST /api/v1/auth/logout`

**Headers:**
```
Authorization: Bearer {jwt_token}
```

**Success Response:** `200 OK`
```json
{
  "message": "Logged out successfully"
}
```

---

### Refresh Token

Get a new JWT token before expiration.

**Endpoint:** `POST /api/v1/auth/refresh`

**Headers:**
```
Authorization: Bearer {jwt_token}
```

**Success Response:** `200 OK`
```json
{
  "token": "new_jwt_token_here",
  "expires_at": "2024-10-20T12:00:00Z"
}
```

**Error Responses:**
- `401 Unauthorized` - Invalid or expired token

---

### Verify Email

Verify user's email address.

**Endpoint:** `POST /api/v1/auth/verify-email`

**Request Body:**
```json
{
  "token": "email_verification_token"
}
```

**Success Response:** `200 OK`
```json
{
  "message": "Email verified successfully"
}
```

---

## Wallet Management

All wallet endpoints require authentication.

### Get Balance

Get current wallet balance.

**Endpoint:** `GET /api/v1/wallet/balance`

**Headers:**
```
Authorization: Bearer {jwt_token}
```

**Success Response:** `200 OK`
```json
{
  "balance": "1500.00",
  "currency": "USD",
  "last_updated": "2024-10-19T12:00:00Z"
}
```

**Note:** Balance is encrypted in database and decrypted on-the-fly.

---

### Deposit Funds

Add funds to wallet.

**Endpoint:** `POST /api/v1/wallet/deposit`

**Headers:**
```
Authorization: Bearer {jwt_token}
```

**Request Body:**
```json
{
  "amount": "100.00",
  "payment_method": "credit_card",
  "payment_reference": "ref_12345"
}
```

**Validation:**
- Amount: Min $10.00, Max $10,000.00
- Must be positive number with max 2 decimal places

**Success Response:** `201 Created`
```json
{
  "transaction_id": "uuid",
  "amount": "100.00",
  "new_balance": "1600.00",
  "status": "completed",
  "created_at": "2024-10-19T12:00:00Z"
}
```

**Error Responses:**
- `400 Bad Request` - Invalid amount
- `402 Payment Required` - Payment failed
- `429 Too Many Requests` - Rate limit exceeded

---

### Withdraw Funds

Withdraw funds from wallet.

**Endpoint:** `POST /api/v1/wallet/withdraw`

**Headers:**
```
Authorization: Bearer {jwt_token}
```

**Request Body:**
```json
{
  "amount": "50.00",
  "withdrawal_method": "bank_transfer",
  "account_details": {
    "account_number": "1234567890",
    "routing_number": "123456789"
  }
}
```

**Validation:**
- Amount: Min $20.00, Max $5,000.00 per transaction
- Must have sufficient balance
- Cannot withdraw pending bet amounts

**Success Response:** `201 Created`
```json
{
  "transaction_id": "uuid",
  "amount": "50.00",
  "new_balance": "1550.00",
  "status": "pending",
  "estimated_completion": "2024-10-20T12:00:00Z",
  "created_at": "2024-10-19T12:00:00Z"
}
```

**Error Responses:**
- `400 Bad Request` - Invalid amount or details
- `402 Payment Required` - Insufficient funds
- `403 Forbidden` - Pending bets exist
- `429 Too Many Requests` - Rate limit exceeded

---

### Get Transaction History

Get wallet transaction history.

**Endpoint:** `GET /api/v1/wallet/transactions`

**Headers:**
```
Authorization: Bearer {jwt_token}
```

**Query Parameters:**
- `limit` (optional): Number of transactions (default: 50, max: 100)
- `offset` (optional): Pagination offset (default: 0)
- `type` (optional): Filter by type (deposit, withdrawal, bet, win, refund)
- `from_date` (optional): Start date (ISO 8601)
- `to_date` (optional): End date (ISO 8601)

**Example:**
```
GET /api/v1/wallet/transactions?limit=20&type=bet&from_date=2024-10-01
```

**Success Response:** `200 OK`
```json
{
  "transactions": [
    {
      "id": "uuid",
      "type": "deposit",
      "amount": "100.00",
      "balance_before": "1500.00",
      "balance_after": "1600.00",
      "description": "Credit card deposit",
      "status": "completed",
      "created_at": "2024-10-19T12:00:00Z"
    },
    {
      "id": "uuid",
      "type": "bet",
      "amount": "-50.00",
      "balance_before": "1600.00",
      "balance_after": "1550.00",
      "description": "Bet on Lakers vs Warriors",
      "metadata": {
        "bet_id": "uuid",
        "event_id": "uuid"
      },
      "status": "completed",
      "created_at": "2024-10-19T11:30:00Z"
    }
  ],
  "pagination": {
    "total": 150,
    "limit": 20,
    "offset": 0,
    "has_more": true
  }
}
```

---

## Betting

### Get Events

List available betting events.

**Endpoint:** `GET /api/v1/betting/events`

**Headers:**
```
Authorization: Bearer {jwt_token}
```

**Query Parameters:**
- `sport` (optional): Filter by sport (football, basketball, baseball, etc.)
- `status` (optional): Filter by status (UPCOMING, LIVE, FINISHED)
- `league` (optional): Filter by league name

**Example:**
```
GET /api/v1/betting/events?sport=football&status=UPCOMING
```

**Success Response:** `200 OK`
```json
{
  "events": [
    {
      "id": "uuid",
      "sport": "football",
      "league": "NFL",
      "home_team": "Los Angeles Lakers",
      "away_team": "Golden State Warriors",
      "event_date": "2024-10-25T19:00:00Z",
      "status": "UPCOMING",
      "home_score": null,
      "away_score": null,
      "odds": {
        "moneyline": {
          "home": "-150",
          "away": "+130"
        },
        "spread": {
          "line": "-3.5",
          "home_odds": "-110",
          "away_odds": "-110"
        },
        "total": {
          "points": "220.5",
          "over_odds": "-105",
          "under_odds": "-115"
        }
      }
    }
  ],
  "count": 1
}
```

---

### Get Event Details

Get detailed information about a specific event.

**Endpoint:** `GET /api/v1/betting/events/{event_id}`

**Headers:**
```
Authorization: Bearer {jwt_token}
```

**Success Response:** `200 OK`
```json
{
  "id": "uuid",
  "sport": "football",
  "league": "NFL",
  "home_team": "Los Angeles Lakers",
  "away_team": "Golden State Warriors",
  "event_date": "2024-10-25T19:00:00Z",
  "status": "UPCOMING",
  "home_score": null,
  "away_score": null,
  "venue": "Staples Center",
  "odds": {
    "moneyline": {
      "home": "-150",
      "away": "+130"
    },
    "spread": {
      "line": "-3.5",
      "home_odds": "-110",
      "away_odds": "-110"
    },
    "total": {
      "points": "220.5",
      "over_odds": "-105",
      "under_odds": "-115"
    }
  },
  "statistics": {
    "home_record": "10-5",
    "away_record": "8-7"
  }
}
```

**Error Responses:**
- `404 Not Found` - Event not found

---

### Place Bet

Place a bet on an event.

**Endpoint:** `POST /api/v1/betting/bets`

**Headers:**
```
Authorization: Bearer {jwt_token}
```

**Request Body:**
```json
{
  "event_id": "uuid",
  "bet_type": "MONEYLINE",
  "selection": "HOME",
  "amount": "50.00",
  "odds": "-150"
}
```

**Bet Types:**
- `MONEYLINE` - Pick the winner (selection: HOME, AWAY)
- `SPREAD` - Point spread (selection: HOME, AWAY)
- `TOTAL` - Over/Under (selection: OVER, UNDER)

**Validation:**
- Amount: Min $1.00, Max $500.00 (default)
- Must have sufficient balance
- Event must be UPCOMING (not started)
- Odds must match current odds (within tolerance)
- Respects daily/weekly/monthly betting limits

**Success Response:** `201 Created`
```json
{
  "bet": {
    "id": "uuid",
    "event_id": "uuid",
    "bet_type": "MONEYLINE",
    "selection": "HOME",
    "odds": "-150",
    "amount": "50.00",
    "potential_win": "33.33",
    "status": "PENDING",
    "created_at": "2024-10-19T12:00:00Z"
  },
  "wallet": {
    "new_balance": "1500.00"
  }
}
```

**Error Responses:**
- `400 Bad Request` - Invalid bet parameters
- `402 Payment Required` - Insufficient funds
- `403 Forbidden` - Betting limit exceeded or self-excluded
- `404 Not Found` - Event not found
- `409 Conflict` - Event already started or odds changed
- `429 Too Many Requests` - Rate limit (5 bets per minute)

**Rate Limit:** 5 bets per minute per user

---

### Get User Bets

Get user's betting history.

**Endpoint:** `GET /api/v1/betting/bets`

**Headers:**
```
Authorization: Bearer {jwt_token}
```

**Query Parameters:**
- `limit` (optional): Number of bets (default: 50, max: 100)
- `offset` (optional): Pagination offset
- `status` (optional): Filter by status (PENDING, WON, LOST, CANCELLED, REFUNDED)

**Success Response:** `200 OK`
```json
{
  "bets": [
    {
      "id": "uuid",
      "event_id": "uuid",
      "event": {
        "home_team": "Los Angeles Lakers",
        "away_team": "Golden State Warriors",
        "event_date": "2024-10-25T19:00:00Z"
      },
      "bet_type": "MONEYLINE",
      "selection": "HOME",
      "odds": "-150",
      "amount": "50.00",
      "potential_win": "33.33",
      "status": "PENDING",
      "created_at": "2024-10-19T12:00:00Z",
      "settled_at": null
    }
  ],
  "summary": {
    "total_bets": 25,
    "total_wagered": "1250.00",
    "total_won": "450.00",
    "pending_count": 3,
    "pending_amount": "150.00"
  }
}
```

---

### Get Bet Details

Get details of a specific bet.

**Endpoint:** `GET /api/v1/betting/bets/{bet_id}`

**Headers:**
```
Authorization: Bearer {jwt_token}
```

**Success Response:** `200 OK`
```json
{
  "id": "uuid",
  "event_id": "uuid",
  "event": {
    "sport": "football",
    "league": "NFL",
    "home_team": "Los Angeles Lakers",
    "away_team": "Golden State Warriors",
    "event_date": "2024-10-25T19:00:00Z",
    "status": "FINISHED",
    "home_score": 105,
    "away_score": 98
  },
  "bet_type": "MONEYLINE",
  "selection": "HOME",
  "odds": "-150",
  "amount": "50.00",
  "potential_win": "33.33",
  "actual_win": "33.33",
  "status": "WON",
  "created_at": "2024-10-19T12:00:00Z",
  "settled_at": "2024-10-25T21:30:00Z"
}
```

**Error Responses:**
- `404 Not Found` - Bet not found or not owned by user

---

## Responsible Gambling Limits

### Get Current Limits

Get user's current betting limits.

**Endpoint:** `GET /api/v1/limits`

**Headers:**
```
Authorization: Bearer {jwt_token}
```

**Success Response:** `200 OK`
```json
{
  "daily_loss_limit": "1000.00",
  "weekly_loss_limit": "5000.00",
  "monthly_loss_limit": "15000.00",
  "daily_bet_limit": "2000.00",
  "weekly_bet_limit": "10000.00",
  "monthly_bet_limit": "30000.00",
  "max_single_bet": "500.00",
  "self_excluded": false,
  "self_exclusion_until": null,
  "current_period_stats": {
    "daily_loss": "150.00",
    "weekly_loss": "350.00",
    "monthly_loss": "1200.00",
    "daily_wagered": "300.00",
    "weekly_wagered": "1500.00",
    "monthly_wagered": "5000.00"
  }
}
```

---

### Update Limits

Update betting limits (decrease only, or increase after cooling period).

**Endpoint:** `PUT /api/v1/limits`

**Headers:**
```
Authorization: Bearer {jwt_token}
```

**Request Body:**
```json
{
  "daily_loss_limit": "500.00",
  "weekly_loss_limit": "2500.00",
  "monthly_loss_limit": "10000.00",
  "max_single_bet": "200.00"
}
```

**Rules:**
- Decreases take effect immediately
- Increases require 24-hour cooling period
- Cannot set limits higher than platform maximums

**Success Response:** `200 OK`
```json
{
  "message": "Limits updated successfully",
  "limits": {
    "daily_loss_limit": "500.00",
    "effective_at": "2024-10-19T12:00:00Z"
  },
  "cooling_period": null
}
```

**If Cooling Period Required:**
```json
{
  "message": "Limit increase pending",
  "limits": {
    "daily_loss_limit": "500.00",
    "effective_at": "2024-10-20T12:00:00Z"
  },
  "cooling_period": "24 hours"
}
```

---

### Self-Exclude

Voluntarily exclude from betting.

**Endpoint:** `POST /api/v1/limits/self-exclude`

**Headers:**
```
Authorization: Bearer {jwt_token}
```

**Request Body:**
```json
{
  "duration_days": 30,
  "reason": "Taking a break"
}
```

**Duration Options:**
- Minimum: 7 days
- Maximum: 365 days
- Cannot be reversed once set

**Success Response:** `200 OK`
```json
{
  "message": "Self-exclusion activated",
  "excluded_until": "2024-11-19T12:00:00Z",
  "message": "You will not be able to place bets until this date"
}
```

**Warning:** This action cannot be undone until the exclusion period expires.

---

## User Profile

### Get Profile

Get user profile information.

**Endpoint:** `GET /api/v1/user/profile`

**Headers:**
```
Authorization: Bearer {jwt_token}
```

**Success Response:** `200 OK`
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "phone": "+1234567890",
  "date_of_birth": "1990-01-01",
  "address": "123 Main St, City, State 12345",
  "verified": true,
  "kyc_verified": true,
  "account_status": "ACTIVE",
  "created_at": "2024-01-01T12:00:00Z",
  "last_login": "2024-10-19T12:00:00Z"
}
```

---

### Update Profile

Update user profile information.

**Endpoint:** `PUT /api/v1/user/profile`

**Headers:**
```
Authorization: Bearer {jwt_token}
```

**Request Body:**
```json
{
  "first_name": "John",
  "last_name": "Doe",
  "phone": "+1234567890",
  "address": "456 New St, City, State 12345"
}
```

**Note:** Email and date_of_birth cannot be changed.

**Success Response:** `200 OK`
```json
{
  "message": "Profile updated successfully",
  "user": {
    "id": "uuid",
    "first_name": "John",
    "last_name": "Doe",
    "phone": "+1234567890",
    "address": "456 New St, City, State 12345"
  }
}
```

---

### Get Activity Log

Get user activity history.

**Endpoint:** `GET /api/v1/user/activity`

**Headers:**
```
Authorization: Bearer {jwt_token}
```

**Query Parameters:**
- `limit` (optional): Default 50, max 100
- `offset` (optional): Pagination offset

**Success Response:** `200 OK`
```json
{
  "activities": [
    {
      "type": "LOGIN",
      "description": "Successful login",
      "ip_address": "192.168.1.1",
      "user_agent": "Mozilla/5.0...",
      "timestamp": "2024-10-19T12:00:00Z"
    },
    {
      "type": "BET_PLACED",
      "description": "Placed bet on Lakers vs Warriors",
      "amount": "50.00",
      "timestamp": "2024-10-19T11:30:00Z"
    },
    {
      "type": "DEPOSIT",
      "description": "Wallet deposit",
      "amount": "100.00",
      "timestamp": "2024-10-19T11:00:00Z"
    }
  ],
  "pagination": {
    "total": 150,
    "limit": 50,
    "offset": 0
  }
}
```

---

## System

### Health Check

Check if the API is running.

**Endpoint:** `GET /health`

**No authentication required**

**Success Response:** `200 OK`
```json
{
  "status": "healthy",
  "timestamp": "2024-10-19T12:00:00Z",
  "version": "0.1.0"
}
```

---

### Metrics

Get system metrics (admin only).

**Endpoint:** `GET /metrics`

**Headers:**
```
Authorization: Bearer {admin_jwt_token}
```

**Success Response:** `200 OK`
```json
{
  "uptime_seconds": 86400,
  "total_users": 1250,
  "active_users": 450,
  "total_bets_today": 3500,
  "total_wagered_today": "175000.00",
  "database_status": "healthy",
  "cache_hit_rate": 0.95
}
```

---

## Error Responses

All errors follow this format:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": "Additional context (optional)",
    "timestamp": "2024-10-19T12:00:00Z"
  }
}
```

### Common Error Codes

| Status Code | Error Code | Description |
|------------|------------|-------------|
| 400 | `VALIDATION_ERROR` | Invalid request data |
| 401 | `UNAUTHORIZED` | Missing or invalid authentication |
| 403 | `FORBIDDEN` | Insufficient permissions or self-excluded |
| 404 | `NOT_FOUND` | Resource not found |
| 409 | `CONFLICT` | Resource conflict (e.g., duplicate email) |
| 422 | `UNPROCESSABLE_ENTITY` | Request understood but cannot be processed |
| 423 | `LOCKED` | Account locked |
| 429 | `RATE_LIMIT_EXCEEDED` | Too many requests |
| 500 | `INTERNAL_ERROR` | Server error |
| 503 | `SERVICE_UNAVAILABLE` | Service temporarily unavailable |

---

## Rate Limits

Rate limits are applied per user or IP address:

| Endpoint | Rate Limit |
|----------|------------|
| Register | 5 per hour per IP |
| Login | 10 per minute per IP |
| Place Bet | 5 per minute per user |
| Deposit | 10 per hour per user |
| Withdraw | 5 per hour per user |
| Other endpoints | 100 per minute per user |

**Rate Limit Headers:**

All responses include rate limit information:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1634659200
```

**Rate Limit Exceeded Response:** `429 Too Many Requests`
```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Too many requests. Please try again in 60 seconds.",
    "retry_after": 60
  }
}
```

---

## Authentication

Most endpoints require JWT authentication:

1. Obtain JWT token via `/api/v1/auth/login`
2. Include token in Authorization header: `Authorization: Bearer {token}`
3. Token expires after 24 hours (default)
4. Refresh token before expiration via `/api/v1/auth/refresh`

**Security Notes:**
- Tokens are signed with HS256
- Store tokens securely (never in localStorage for production)
- Use HTTPS in production
- Implement CSRF protection for web clients

---

## Pagination

List endpoints support pagination:

**Query Parameters:**
- `limit`: Items per page (default: 50, max: 100)
- `offset`: Starting position (default: 0)

**Response Format:**
```json
{
  "items": [...],
  "pagination": {
    "total": 150,
    "limit": 50,
    "offset": 0,
    "has_more": true
  }
}
```

---

## Filtering & Sorting

Some endpoints support filtering and sorting:

**Example:**
```
GET /api/v1/wallet/transactions?type=bet&from_date=2024-10-01&sort=created_at&order=desc
```

---

## Webhooks (Future Feature)

Webhook notifications for important events:
- Bet won/lost
- Deposit/withdrawal completed
- Limit reached
- Self-exclusion activated

---

## SDKs & Libraries

Official SDKs (planned):
- JavaScript/TypeScript
- Python
- Java
- PHP

---

## API Versioning

Current version: **v1**

Breaking changes will be released as new versions (v2, v3, etc.)
- Old versions supported for 6 months after new version release
- Version specified in URL: `/api/v1/...`

---

## Support

For API support:
- Email: api-support@footballheritage.com
- Documentation: https://docs.footballheritage.com
- Status Page: https://status.footballheritage.com

---

## Changelog

### Version 1.0.0 (2024-10-19)
- Initial API release
- Authentication endpoints
- Wallet management
- Betting functionality
- Responsible gambling limits
- User profile management

---

**Last Updated:** October 19, 2024
**API Version:** 1.0.0
**Documentation Version:** 1.0.0