# Deployment Guide: Render + Supabase

## Step 1: Set Up Supabase Database

1. Go to [Supabase Dashboard](https://supabase.com/dashboard)
2. Create new project (if not already created)
3. In Project Settings → Database, copy the **Connection String (URI)**
   - Should look like: `postgresql://user:password@host:5432/dbname`

## Step 2: Prepare Your Code

✅ Already done:
- `Procfile` created (tells Render how to run the app)
- `runtime.txt` created (Python version specified)
- `requirements.txt` updated with `gunicorn` and `psycopg2-binary`
- `app.py` updated to support PostgreSQL via `DATABASE_URL` env var

## Step 3: Deploy to Render

### Option A: Using GitHub (Recommended)

1. **Push code to GitHub**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
   git push -u origin main
   ```

2. **Create Render Account**
   - Go to [render.com](https://render.com)
   - Sign up with GitHub account
   - Connect GitHub

3. **Create New Web Service**
   - Click "New +" → "Web Service"
   - Connect your GitHub repo
   - Fill in details:
     - **Name**: diabetes-app (or your choice)
     - **Environment**: Python 3
     - **Build Command**: `pip install -r requirements.txt`
     - **Start Command**: `gunicorn app:app`
     - **Region**: Choose closest region
     - **Plan**: Free

4. **Add Environment Variables**
   - Click "Advanced"
   - Add environment variables:
     ```
     DATABASE_URL = [Paste Supabase PostgreSQL URI]
     SECRET_KEY = [Generate a random secret key]
     ```
   - To generate SECRET_KEY: `python -c "import secrets; print(secrets.token_hex(32))"`

5. **Deploy**
   - Click "Create Web Service"
   - Wait for deployment (2-3 minutes)
   - Your app will be at: `https://your-app-name.onrender.com`

### Option B: Using Render CLI (Manual)

```bash
# 1. Install Render CLI
npm install -g @render-oss/cli

# 2. Login to Render
render login

# 3. Deploy
render deploy
```

## Step 4: Initialize Database Tables

After first deployment:

1. SSH into Render service or use Supabase console
2. Create tables (your `models.py` defines them)
3. Seed default users

**Option A: Use Flask shell**
```bash
# From local machine with DATABASE_URL set:
export DATABASE_URL="your-supabase-uri"
python -c "from app import app, db; app.app_context().push(); db.create_all()"
```

**Option B: Use Python script to seed data**
```bash
python -c "
from app import app, db
from models import User
from werkzeug.security import generate_password_hash

app.app_context().push()
db.create_all()

# Seed users
admin = User(email='admin@example.com', role='admin', password_hash=generate_password_hash('admin123'))
clinician = User(email='clinician@example.com', role='clinician', password_hash=generate_password_hash('password123'))
patient = User(email='patient@example.com', role='patient', password_hash=generate_password_hash('password123'))

db.session.add_all([admin, clinician, patient])
db.session.commit()
print('Users created!')
"
```

## Step 5: Test Your App

1. Visit `https://your-app-name.onrender.com`
2. Login with:
   - Email: `patient@example.com`
   - Password: `password123`

## Troubleshooting

**Error: "import: No module named 'ml'"**
- You're missing ML modules. The `/ml/` directory doesn't exist.
- Create placeholder files or implement missing modules.

**Error: "relation 'users' does not exist"**
- Database tables weren't created. Run the initialization script above.

**Port/Connection Error**
- Ensure `DATABASE_URL` is set correctly in Render environment variables
- Check Supabase credentials

**Build Fails**
- Check build logs in Render dashboard
- Ensure all dependencies in `requirements.txt` are compatible

## Production Considerations

1. **Use strong SECRET_KEY** - Already added
2. **Set `FLASK_ENV=production`** - Add to Render environment
3. **Monitor logs** - Check Render logs regularly
4. **Database backups** - Supabase provides automatic backups on paid plans
5. **Custom domain** - Add in Render settings (requires DNS)

## Next Steps

- [ ] Create `/ml/` directory with missing modules
- [ ] Create `/templates/` and `/static/` with UI
- [ ] Set up automated backups
- [ ] Add error monitoring (Sentry, etc.)
- [ ] Implement email alerts
