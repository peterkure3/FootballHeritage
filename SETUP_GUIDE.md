# Football Heritage - Quick Setup Guide

## 🚀 Getting Started

### **1. Database Setup**

Run the migration to add external tracking columns:

```bash
cd backend
sqlx migrate run
```

Or manually run the SQL:
```sql
-- Add external tracking to events
ALTER TABLE events 
ADD COLUMN IF NOT EXISTS external_id VARCHAR(255),
ADD COLUMN IF NOT EXISTS external_source VARCHAR(50),
ADD COLUMN IF NOT EXISTS created_by UUID,
ADD COLUMN IF NOT EXISTS updated_by UUID;

CREATE UNIQUE INDEX IF NOT EXISTS idx_events_external 
ON events(external_id, external_source) 
WHERE external_id IS NOT NULL;

-- Add bet settlement tracking
ALTER TABLE bets
ADD COLUMN IF NOT EXISTS settled_by UUID,
ADD COLUMN IF NOT EXISTS settled_at TIMESTAMP;

-- Create admin logs table
CREATE TABLE IF NOT EXISTS admin_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    admin_id UUID NOT NULL REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    target_type VARCHAR(50),
    target_id UUID,
    details JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

---

### **2. Import BetPawa Data**

Install Node.js dependencies:
```bash
cd backend
npm install pg
```

Run the importer:
```bash
node scripts/import_betpawa_data.js
```

**What it does:**
- ✅ Fetches live sports data from BetPawa API
- ✅ Imports Soccer, Basketball, Tennis, eSports events
- ✅ Extracts odds (Moneyline, Spread, Over/Under)
- ✅ Auto-updates existing events

**Output:**
```
🚀 Starting BetPawa data import...
📡 Fetching data from BetPawa API...

📊 Processing SOCCER events...
   ✅ Manchester United vs Liverpool
   ✅ Arsenal vs Chelsea
   
📊 Processing BASKETBALL events...
   ✅ Lakers vs Warriors
   
====================================================
📈 Import Summary:
   ✅ Imported: 25
   🔄 Updated: 5
   ❌ Errors: 0
====================================================
✨ Import completed successfully!
```

---

### **3. Start the Backend**

```bash
cd backend
cargo run
```

Backend runs on: `https://localhost:8080`

---

### **4. Start the Frontend**

```bash
cd frontend
npm run dev
```

Frontend runs on: `http://localhost:5173`

---

## 🎯 Admin Features

### **Access Admin Dashboard**

1. Login with admin account
2. Click the 🛡️ icon in navbar to switch to Admin View
3. Navigate to admin pages:
   - **Dashboard** - `/admin/dashboard`
   - **Manage Events** - `/admin/events`
   - **Manage Bets** - `/admin/bets`

---

### **Manage Events**

**Create Event:**
1. Go to `/admin/events`
2. Click "Create Event" button
3. Fill in the form:
   - Sport & League
   - Home/Away Teams
   - Event Date & Time
   - Betting Odds (optional)
4. Click "Create Event"

**Edit Event:**
1. Find event in the list
2. Click "Edit" button
3. Update fields
4. Click "Update Event"

**Delete Event:**
1. Click "Delete" button
2. Confirm deletion
3. Note: Can't delete events with existing bets

---

### **Manage Bets**

**View Bets:**
- Filter by status (Pending, Won, Lost)
- Filter by sport
- Search by user

**Settle Bet:**
1. Find pending bet
2. Click "Settle" button
3. Choose "WON" or "LOST"
4. Winnings auto-credited to user wallet

**Void Bet:**
1. Click "Void" button
2. Stake auto-refunded to user

---

## 📊 API Endpoints

### **Events CRUD**
```
GET    /api/v1/admin/events              # List all events
GET    /api/v1/admin/events/:id          # Get single event
POST   /api/v1/admin/events              # Create event
PUT    /api/v1/admin/events/:id          # Update event
DELETE /api/v1/admin/events/:id          # Delete event
PUT    /api/v1/admin/events/:id/status   # Update status
```

### **Bets CRUD**
```
GET    /api/v1/admin/bets                # List all bets
GET    /api/v1/admin/bets/:id            # Get single bet
PUT    /api/v1/admin/bets/:id/settle     # Settle bet (WON/LOST)
PUT    /api/v1/admin/bets/:id/void       # Void bet & refund
DELETE /api/v1/admin/bets/:id            # Delete bet
```

---

## 🔄 Automated Data Import

### **Schedule BetPawa Import**

**Windows (Task Scheduler):**
```powershell
# Run every hour
schtasks /create /tn "BetPawa Import" /tr "node D:\Github\FootballHeritgae\backend\scripts\import_betpawa_data.js" /sc hourly
```

**Linux/Mac (Cron):**
```bash
# Add to crontab (run every hour)
0 * * * * cd /path/to/backend && node scripts/import_betpawa_data.js
```

---

## 🎨 Features Implemented

### **Backend (Rust)**
- ✅ Full CRUD for Events
- ✅ Full CRUD for Bets
- ✅ Bet settlement with wallet integration
- ✅ Admin audit logging
- ✅ External data tracking
- ✅ Transaction safety

### **Frontend (React)**
- ✅ Admin Events page with grid view
- ✅ Event creation/edit form
- ✅ Search & filter events
- ✅ Status badges & icons
- ✅ Empty states
- ✅ Loading states
- ✅ Toast notifications

### **Data Import**
- ✅ BetPawa API integration
- ✅ Auto-import sports data
- ✅ Upsert logic (insert or update)
- ✅ Support for 4 sports
- ✅ Odds extraction

---

## 🐛 Troubleshooting

### **Migration Fails**
```bash
# Check database connection
psql -U postgres -d football_heritage

# Manually run migration
psql -U postgres -d football_heritage -f backend/migrations/20251025000001_add_external_tracking.sql
```

### **BetPawa Import Fails**
```bash
# Check if pg is installed
npm list pg

# Install if missing
npm install pg

# Check database URL
echo $DATABASE_URL
```

### **Backend Won't Start**
```bash
# Check if port 8080 is in use
netstat -ano | findstr :8080

# Kill process if needed
taskkill /PID <process_id> /F
```

### **Frontend Build Errors**
```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install
```

---

## 📝 Next Steps

1. ✅ Run database migration
2. ✅ Import BetPawa data
3. ✅ Test event creation in admin panel
4. ✅ Test bet management
5. ✅ Schedule automated imports
6. 🚀 Deploy to production!

---

## 🎯 Production Checklist

- [ ] Update `.env` with production database URL
- [ ] Set strong JWT_SECRET (min 32 chars)
- [ ] Set strong ENCRYPTION_KEY (exactly 32 chars)
- [ ] Enable HTTPS with valid SSL certificates
- [ ] Configure CORS for production domain
- [ ] Set up database backups
- [ ] Configure monitoring & alerts
- [ ] Test all admin features
- [ ] Load test with concurrent users
- [ ] Set up CI/CD pipeline

---

## 📚 Documentation

- **Backend API**: See `backend/src/handlers/admin/`
- **Frontend Components**: See `frontend/src/components/`
- **Database Schema**: See `backend/migrations/`
- **BetPawa Importer**: See `backend/scripts/import_betpawa_data.js`

---

## 🆘 Support

For issues or questions:
1. Check the troubleshooting section above
2. Review error logs in terminal
3. Check browser console for frontend errors
4. Verify database connection and migrations

---

**Happy Betting! 🎰**
