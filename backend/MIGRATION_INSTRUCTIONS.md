# 🗄️ Database Migration Instructions

## Step 1: Run the Admin System Migration

### **Option A: Using psql (Recommended)**

```bash
# Navigate to backend folder
cd backend

# Run the migration
psql -h localhost -p 5432 -U postgres -d football_heritage -f migrations/20251024000001_add_admin_system.sql
```

Enter your PostgreSQL password when prompted.

### **Option B: Using pgAdmin**

1. Open pgAdmin
2. Connect to your `football_heritage` database
3. Open Query Tool
4. Load file: `backend/migrations/20251024000001_add_admin_system.sql`
5. Click Execute (F5)

### **Option C: Using DBeaver/DataGrip**

1. Open your SQL client
2. Connect to `football_heritage` database
3. Open the migration file
4. Execute the script

---

## ✅ What This Migration Does

### **1. Adds Role System**
- Adds `role` column to `users` table
- Possible values: `user`, `admin`, `superadmin`
- All existing users get `user` role

### **2. Creates Admin Tables**

| Table | Purpose |
|-------|---------|
| `admin_logs` | Tracks all admin actions (audit trail) |
| `platform_metrics` | Daily platform statistics |
| `fraud_alerts` | Suspicious activity alerts |

### **3. Adds Event Tracking**
- `created_by`, `updated_by`, `settled_by` columns to `events` table
- Tracks which admin created/modified events

### **4. Creates Helper Functions**
- `update_platform_metrics()` - Updates daily metrics
- `log_admin_action()` - Logs admin actions
- `admin_dashboard_summary` view - Quick dashboard stats

### **5. Creates Test Admin User**

**⚠️ IMPORTANT: Change this password immediately!**

```
Email: admin@footballheritage.com
Password: Admin123!
Role: superadmin
```

---

## 🧪 Verify Migration Success

Run these queries to verify:

```sql
-- Check role column exists
SELECT email, role, is_active FROM users LIMIT 5;

-- Check admin user exists
SELECT email, role FROM users WHERE role IN ('admin', 'superadmin');

-- Check new tables exist
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name IN ('admin_logs', 'platform_metrics', 'fraud_alerts');

-- Check dashboard view
SELECT * FROM admin_dashboard_summary;
```

Expected output:
- Users have `role` column
- Admin user exists with email `admin@footballheritage.com`
- 3 new tables exist
- Dashboard view returns metrics

---

## 🔐 Security: Change Admin Password

### **Method 1: Using Application (After backend is running)**

1. Login as admin
2. Go to profile settings
3. Change password

### **Method 2: Using SQL (Before backend is running)**

```sql
-- Generate new password hash using Argon2
-- You'll need to use the backend's hash function or an online tool

-- Update admin password (replace with your hash)
UPDATE users 
SET password_hash = 'YOUR_NEW_ARGON2_HASH_HERE'
WHERE email = 'admin@footballheritage.com';
```

### **Method 3: Create New Admin User**

```sql
-- Create your own admin user
INSERT INTO users (
    email,
    password_hash,
    first_name,
    last_name,
    date_of_birth,
    role,
    is_verified,
    is_active
) VALUES (
    'your.email@example.com',
    'YOUR_ARGON2_HASH',  -- Use backend to generate this
    'Your',
    'Name',
    '1990-01-01',
    'superadmin',
    true,
    true
);

-- Create wallet for new admin
INSERT INTO wallets (user_id, encrypted_balance, encryption_iv)
SELECT id, 'encrypted_0', 'test_iv'
FROM users WHERE email = 'your.email@example.com';
```

---

## 📊 New Database Schema

### **users table (updated)**
```sql
+ role VARCHAR(20) DEFAULT 'user'  -- NEW
```

### **admin_logs table (new)**
```sql
id UUID PRIMARY KEY
admin_id UUID  -- Who performed the action
action VARCHAR(100)  -- What action (e.g., 'suspend_user', 'create_event')
target_type VARCHAR(50)  -- What was affected ('user', 'event', 'bet')
target_id UUID  -- ID of affected entity
details JSONB  -- Additional details
ip_address VARCHAR(45)
user_agent TEXT
created_at TIMESTAMP
```

### **platform_metrics table (new)**
```sql
id UUID PRIMARY KEY
date DATE UNIQUE  -- Metrics for this date
total_users INTEGER
new_users INTEGER
active_users INTEGER
total_bets INTEGER
total_bet_amount DECIMAL(15,2)
total_payouts DECIMAL(15,2)
platform_revenue DECIMAL(15,2)
total_deposits DECIMAL(15,2)
total_withdrawals DECIMAL(15,2)
created_at TIMESTAMP
updated_at TIMESTAMP
```

### **fraud_alerts table (new)**
```sql
id UUID PRIMARY KEY
user_id UUID
alert_type VARCHAR(50)  -- Type of suspicious activity
severity VARCHAR(20)  -- low, medium, high, critical
description TEXT
metadata JSONB
status VARCHAR(20)  -- pending, investigating, resolved, false_positive
reviewed_by UUID  -- Admin who reviewed
reviewed_at TIMESTAMP
notes TEXT
created_at TIMESTAMP
updated_at TIMESTAMP
```

### **events table (updated)**
```sql
+ created_by UUID  -- NEW: Admin who created event
+ updated_by UUID  -- NEW: Admin who last updated
+ settled_by UUID  -- NEW: Admin who settled bets
+ settled_at TIMESTAMP  -- NEW: When bets were settled
```

---

## 🚀 Next Steps After Migration

1. ✅ **Verify migration** using queries above
2. 🔐 **Change admin password** immediately
3. 🔨 **Rebuild backend** to include admin endpoints
4. 🎨 **Access admin dashboard** at `/admin`

---

## 🐛 Troubleshooting

### **Error: relation "users" does not exist**
- Make sure you're connected to the correct database (`football_heritage`)
- Run the main schema.sql first if this is a fresh database

### **Error: column "role" already exists**
- Migration was already run
- Safe to ignore, or run: `DROP TABLE IF EXISTS admin_logs, platform_metrics, fraud_alerts CASCADE;`

### **Error: password authentication failed**
- Check your PostgreSQL password
- Verify DATABASE_URL in .env file

### **Can't connect to PostgreSQL**
- Make sure PostgreSQL is running
- Check host, port, and database name
- Verify firewall settings

---

## 📝 Migration Summary

**Files Created:**
- ✅ `migrations/20251024000001_add_admin_system.sql` - Main migration
- ✅ `run_migration.ps1` - PowerShell migration runner
- ✅ `MIGRATION_INSTRUCTIONS.md` - This file

**Database Changes:**
- ✅ Added `role` column to users
- ✅ Created 3 new tables (admin_logs, platform_metrics, fraud_alerts)
- ✅ Added tracking columns to events
- ✅ Created helper functions and views
- ✅ Created test admin user

**Ready for:** Backend admin API implementation

---

## ✨ What's Next?

Once migration is complete, I'll implement:

1. **Backend Admin APIs** (Rust handlers)
2. **Admin Dashboard UI** (React components)
3. **User Management Interface**
4. **Event Management Interface**
5. **Analytics & Monitoring**

Let me know when the migration is complete! 🚀
