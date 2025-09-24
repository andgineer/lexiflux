# Lexiflux Koyeb Deployment Guide

For Koyeb's free tier.

## Prerequisites

### 1. Requirements
- [Koyeb](https://www.koyeb.com/) account
- GitHub account with Lexiflux repository
- Google/GitHub OAuth applications (for authentication)
- Email account with SMTP setup (Gmail recommended)

### 2. OAuth Application Setup

#### Google OAuth
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or use existing one
3. Enable Google+ API
4. Create OAuth 2.0 credentials
5. Add redirect URI: `https://your-app.koyeb.app/accounts/google/login/callback/`

#### GitHub OAuth (optional)
1. Go to GitHub Settings > Developer settings > OAuth Apps
2. Create new OAuth application
3. Set Authorization callback URL: `https://your-app.koyeb.app/accounts/github/login/callback/`

### 3. Email Setup (Gmail)
1. Enable 2-factor authentication in Gmail
2. Create App Password for Lexiflux
3. Use this password in EMAIL_HOST_PASSWORD setting

## Koyeb Deployment

### 1. Create Application
1. Log into Koyeb Dashboard
2. Click "Create App"
3. Select "Deploy from GitHub"
4. Connect your GitHub repository
5. Choose branch (usually `main`)

### 2. Build Configuration
- **Build command**: `uv pip install --system -r requirements.koyeb.txt && python manage.py collectstatic --noinput`
- **Run command**: `python manage.py migrate && python manage.py runserver 0.0.0.0:$PORT`
- **Port**: `8000`

### 3. Environment Variables Setup

Copy variables from `deploy/koyeb/koyeb-env-template.txt` and set their values:

#### Required variables:
```bash
LEXIFLUX_ENV=koyeb

# Database (provided by Koyeb)
DATABASE_URL=postgresql://username:password@host:port/database

# Django Secret Key (generate new one!)
SECRET_KEY=your-unique-secret-key-here

# Domains
ALLOWED_HOSTS=lexiflux.sorokin.engineer,your-app.koyeb.app
```

#### Authentication variables:
```bash
# Google OAuth
GOOGLE_OAUTH2_CLIENT_ID=your-google-client-id
GOOGLE_OAUTH2_CLIENT_SECRET=your-google-client-secret

# GitHub OAuth (optional)
GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret
```

#### Email variables:
```bash
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-gmail-app-password
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=your-email@gmail.com
```

### 4. Database Setup
1. In Koyeb Dashboard create PostgreSQL service
2. Copy CONNECTION_STRING to DATABASE_URL variable
3. Database will be automatically migrated on startup

### 5. Custom Domain Setup
1. In Koyeb Dashboard go to app settings
2. Add custom domain: `lexiflux.sorokin.engineer`
3. Configure DNS records according to Koyeb instructions

## Manual Deployment

Repository contains GitHub Actions workflow (`.github/workflows/deploy-koyeb.yml`) for manual deployment only.

### GitHub Secrets Setup:
1. Go to Settings > Secrets and variables > Actions
2. Add the following secrets:
   - `KOYEB_API_TOKEN` - API token from Koyeb Dashboard
   - `DATABASE_URL` - PostgreSQL connection string
   - `SECRET_KEY` - Django secret key

Workflow must be triggered manually from GitHub Actions tab (not automatic on push).

## Monitoring and Debugging

### Check Logs
```bash
# In Koyeb Dashboard
1. Go to your application
2. Open "Logs" tab
3. View real-time logs
```

### Local Koyeb Configuration Testing
```bash
python -m venv .venv-koyeb
source .venv-koyeb/bin/activate

uv pip install -r requirements.koyeb.txt

LEXIFLUX_ENV=koyeb DATABASE_URL="postgresql://..." SECRET_KEY="..." python manage.py check --deploy
```

### Local PostgreSQL Testing
```bash
docker-compose -f docker-compose.postgres.yaml up -d

source .venv-koyeb/bin/activate
LEXIFLUX_ENV=koyeb DATABASE_URL="postgresql://lexiflux:password@localhost:5432/lexiflux" SECRET_KEY="test-key" python manage.py runserver
```

## Free Tier Limitations

- **Active time**: 5 hours per month
- **Database**: PostgreSQL 1GB
- **Memory**: 512MB RAM
- **CPU**: Shared
- **Domains**: 1 custom domain

## Troubleshooting

### Issue: Static files not loading
**Solution**: Ensure WhiteNoise is configured correctly and `collectstatic` command executed

### Issue: OAuth not working
**Solution**: Check redirect URIs in OAuth application settings

### Issue: Email not sending
**Solution**: Ensure using App Password for Gmail, not regular password

### Issue: Database unavailable
**Solution**: Check DATABASE_URL correctness and PostgreSQL service is running

## Support

For help:
1. Check logs in Koyeb Dashboard
2. Refer to [Koyeb documentation](https://www.koyeb.com/docs)
3. Create issue in GitHub repository
