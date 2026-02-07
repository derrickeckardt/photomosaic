"""
DEPLOYMENT & SETUP GUIDE - Photo Mosaic Platform
Complete guide for deploying to production
"""

# ============================================================================
# ENVIRONMENT SETUP
# ============================================================================

"""
1. INSTALL DEPENDENCIES

Backend:
$ pip install Flask Flask-CORS Flask-SQLAlchemy Flask-Login
$ pip install Pillow numpy scipy
$ pip install stripe requests
$ pip install gunicorn python-dotenv

Frontend:
$ npm install react react-dom
$ npm install --save-dev @vitejs/plugin-react vite

"""

# ============================================================================
# ENVIRONMENT VARIABLES (.env file)
# ============================================================================

"""
# Flask Configuration
FLASK_ENV=production
SECRET_KEY=your-super-secret-key-change-this

# Database
DATABASE_URL=postgresql://user:password@localhost/mosaic_db
# Or SQLite for development:
# DATABASE_URL=sqlite:///mosaic_platform.db

# Stripe Configuration
STRIPE_PUBLIC_KEY=pk_live_...
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Printful Configuration
PRINTFUL_API_KEY=your_printful_api_key

# Server
ALLOWED_HOSTS=mosaicstudio.com,www.mosaicstudio.com
DEBUG=False
CORS_ORIGINS=https://mosaicstudio.com

# Email (for notifications)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USERNAME=your-email@gmail.com
EMAIL_PASSWORD=your-app-password
EMAIL_FROM=noreply@mosaicstudio.com
"""

# ============================================================================
# INSTALLATION STEPS
# ============================================================================

"""
STEP 1: Clone Repository
$ git clone https://github.com/yourusername/mosaic-platform.git
$ cd mosaic-platform

STEP 2: Create Virtual Environment
$ python -m venv venv
$ source venv/bin/activate  # On Windows: venv\Scripts\activate

STEP 3: Install Dependencies
$ pip install -r requirements.txt

STEP 4: Create .env file
$ cp .env.example .env
# Edit .env with your configuration

STEP 5: Initialize Database
$ python
>>> from backend_api import app, db
>>> with app.app_context():
...     db.create_all()
>>> exit()

STEP 6: Run Locally
$ python backend_api.py
# Backend runs on http://localhost:5000

STEP 7: Run Frontend Dev Server
$ cd frontend
$ npm install
$ npm run dev
# Frontend runs on http://localhost:5173

STEP 8: Test the Application
- Go to http://localhost:5173
- Create an account
- Upload images
- Generate a mosaic
"""

# ============================================================================
# PRODUCTION DEPLOYMENT
# ============================================================================

"""
OPTION 1: DEPLOYING TO HEROKU

1. Install Heroku CLI
   $ curl https://cli-assets.heroku.com/install.sh | sh

2. Create Heroku App
   $ heroku create mosaic-studio
   $ heroku addons:create heroku-postgresql:standard-0 -a mosaic-studio

3. Set Environment Variables
   $ heroku config:set SECRET_KEY=your-secret-key
   $ heroku config:set STRIPE_SECRET_KEY=sk_live_...
   $ heroku config:set PRINTFUL_API_KEY=your-api-key
   # ... set all other variables

4. Create Procfile
   web: gunicorn backend_api:app

5. Create requirements.txt
   Flask==2.3.0
   Flask-CORS==4.0.0
   Flask-SQLAlchemy==3.0.0
   ... (see requirements.txt)

6. Deploy
   $ git push heroku main

7. Verify Deployment
   $ heroku logs --tail
   $ heroku open


OPTION 2: DEPLOYING TO AWS (Recommended for Production)

1. Create EC2 Instance
   - Ubuntu 22.04 LTS
   - t3.medium (recommended starting size)
   - 100GB storage
   - Security group: Allow 80, 443, 22

2. SSH into Instance
   $ ssh -i your-key.pem ubuntu@your-instance-ip

3. Install System Dependencies
   $ sudo apt update
   $ sudo apt install -y python3-pip python3-venv nginx postgresql postgresql-contrib
   $ sudo apt install -y nodejs npm

4. Create Application Directory
   $ mkdir -p /var/www/mosaic-platform
   $ cd /var/www/mosaic-platform
   $ sudo chown ubuntu:ubuntu .

5. Clone Repository
   $ git clone https://github.com/yourusername/mosaic-platform.git .

6. Set Up Backend
   $ python3 -m venv venv
   $ source venv/bin/activate
   $ pip install -r requirements.txt

7. Set Environment Variables
   $ sudo nano /etc/environment
   # Add:
   export FLASK_ENV=production
   export SECRET_KEY=your-secret-key
   export DATABASE_URL=postgresql://user:password@localhost/mosaic_db
   # ... etc

8. Create PostgreSQL Database
   $ sudo -u postgres createdb mosaic_db
   $ sudo -u postgres createuser mosaic_user
   $ sudo -u postgres psql -c "ALTER USER mosaic_user WITH PASSWORD 'secure_password';"
   $ sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE mosaic_db TO mosaic_user;"

9. Initialize Database
   $ source venv/bin/activate
   $ python3 -c "from backend_api import app, db; db.create_all()"

10. Set Up Gunicorn
    $ pip install gunicorn
    # Create /etc/systemd/system/mosaic-backend.service:
    [Unit]
    Description=Mosaic Backend Service
    After=network.target

    [Service]
    User=ubuntu
    WorkingDirectory=/var/www/mosaic-platform
    ExecStart=/var/www/mosaic-platform/venv/bin/gunicorn -w 4 -b 127.0.0.1:5000 backend_api:app
    Restart=always
    RestartSec=10

    [Install]
    WantedBy=multi-user.target

    $ sudo systemctl daemon-reload
    $ sudo systemctl start mosaic-backend
    $ sudo systemctl enable mosaic-backend

11. Build Frontend
    $ cd frontend
    $ npm install
    $ npm run build
    # This creates dist/ folder

12. Set Up Nginx
    $ sudo nano /etc/nginx/sites-available/mosaic-platform
    
    upstream mosaic_backend {
        server 127.0.0.1:5000;
    }

    server {
        listen 80;
        server_name mosaicstudio.com www.mosaicstudio.com;

        # Frontend static files
        location / {
            root /var/www/mosaic-platform/frontend/dist;
            try_files $uri $uri/ /index.html;
        }

        # API proxy
        location /api {
            proxy_pass http://mosaic_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # Webhook endpoint
        location /webhook {
            proxy_pass http://mosaic_backend;
        }
    }

    $ sudo ln -s /etc/nginx/sites-available/mosaic-platform /etc/nginx/sites-enabled/
    $ sudo nginx -t
    $ sudo systemctl restart nginx

13. Set Up SSL with Let's Encrypt
    $ sudo apt install certbot python3-certbot-nginx
    $ sudo certbot --nginx -d mosaicstudio.com -d www.mosaicstudio.com
    # Follow prompts

14. Configure Firewall
    $ sudo ufw allow 22/tcp
    $ sudo ufw allow 80/tcp
    $ sudo ufw allow 443/tcp
    $ sudo ufw enable

15. Set Up Monitoring
    $ pip install sentry-sdk
    # Add to backend_api.py:
    import sentry_sdk
    sentry_sdk.init("your-sentry-dsn")

16. Configure Backups
    # Automatic PostgreSQL backups
    $ sudo nano /etc/postgresql/14/main/postgresql.conf
    # archive_mode = on
    # archive_command = 'cp %p /var/backups/postgresql/%f'

    $ sudo -u postgres mkdir -p /var/backups/postgresql
    $ sudo -u postgres chmod 755 /var/backups/postgresql


OPTION 3: DEPLOYING TO DIGITAL OCEAN

Similar to AWS but use DigitalOcean's App Platform for simpler deployment:

1. Push code to GitHub
2. Connect DigitalOcean App Platform
3. Configure build/run commands
4. Set environment variables in UI
5. Click Deploy

Much simpler than manual AWS setup!
"""

# ============================================================================
# PRINT-ON-DEMAND INTEGRATION SETUP
# ============================================================================

"""
PRINTFUL INTEGRATION

1. Sign Up for Printful
   - Go to https://www.printful.com/
   - Create account and get API key

2. Configure Products
   - Log into Printful Dashboard
   - Navigate to Products > Variants
   - Find product IDs for:
     * Posters (various sizes)
     * Canvas (various sizes)
     * Framed prints (various sizes)

3. Update Database
   In backend_api.py, update default_products with correct printful_product_id values

4. Get API Key
   - Account Settings > API
   - Copy your API key
   - Add to .env: PRINTFUL_API_KEY=your_key

5. Test Integration
   $ python
   >>> from backend_api import send_to_printful, Order
   >>> order = Order.query.first()
   >>> send_to_printful(order)
   >>> # Check Printful dashboard for order


STRIPE INTEGRATION

1. Sign Up for Stripe
   - Go to https://stripe.com/
   - Create account
   - Go to Dashboard

2. Get API Keys
   - Settings > API Keys
   - Copy Publishable Key (starts with pk_)
   - Copy Secret Key (starts with sk_)
   - Add to .env:
     STRIPE_PUBLIC_KEY=pk_...
     STRIPE_SECRET_KEY=sk_...

3. Create Webhook
   - Endpoints > Add endpoint
   - URL: https://yourdomain.com/api/webhook/stripe
   - Events: payment_intent.succeeded, payment_intent.payment_failed
   - Copy Signing Secret
   - Add to .env: STRIPE_WEBHOOK_SECRET=whsec_...

4. Test in Development
   - Use Stripe test keys (pk_test_, sk_test_)
   - Use test card: 4242 4242 4242 4242
   - Any future date for expiry, any CVC

5. Update Frontend
   In frontend_app.jsx, update Stripe key initialization
"""

# ============================================================================
# MONITORING & MAINTENANCE
# ============================================================================

"""
MONITORING

1. Set Up Logging
   - Use CloudWatch (AWS) or similar
   - Log all errors and warnings
   - Set up alerts for failures

2. Monitor Performance
   - Backend: Use New Relic or DataDog
   - Frontend: Use Sentry for JavaScript errors
   - Database: Monitor with native tools

3. Uptime Monitoring
   - Use UptimeRobot or similar
   - Get alerts if site goes down

4. Analytics
   - Google Analytics for frontend
   - Custom logging for mosaic generation stats

MAINTENANCE

Daily:
- Check error logs
- Verify Stripe/Printful integration
- Monitor server health

Weekly:
- Database backups
- Review performance metrics
- Check customer support tickets

Monthly:
- Update dependencies
- Security patches
- Cost analysis

"""

# ============================================================================
# SCALING CONSIDERATIONS
# ============================================================================

"""
AS YOUR PLATFORM GROWS:

1. Mosaic Generation
   - Current: Synchronous (user waits)
   - Scale: Use Celery + Redis for async processing
   - Benefits: User gets instant response, processing in background

2. File Storage
   - Current: Local filesystem
   - Scale: Use S3 for cloud storage
   - Benefits: Unlimited scale, CDN integration

3. Database
   - Current: Single PostgreSQL
   - Scale: Read replicas, connection pooling
   - Benefits: Handle more concurrent users

4. Frontend
   - Current: Nginx static serving
   - Scale: CloudFront CDN
   - Benefits: Faster global delivery

5. Backend
   - Current: Single server
   - Scale: Load balancer + multiple app servers
   - Benefits: Handle traffic spikes

6. Image Processing
   - Current: On same server
   - Scale: Dedicated workers
   - Benefits: Isolate resource-intensive tasks

EXAMPLE SCALED ARCHITECTURE:

Users
  ↓
CloudFront (CDN)
  ↓
Load Balancer
  ↓
[Backend Server 1]  [Backend Server 2]  [Backend Server 3]
  ↓                                            ↓
PostgreSQL Master (with Read Replicas)    Redis
  ↓
Celery Workers (async processing)
  ↓
S3 (image storage)
"""

# ============================================================================
# TROUBLESHOOTING
# ============================================================================

"""
COMMON ISSUES AND SOLUTIONS

Issue: "ModuleNotFoundError: No module named 'PIL'"
Solution: pip install Pillow

Issue: "Database connection refused"
Solution: 
  - Check PostgreSQL is running
  - Verify DATABASE_URL in .env
  - Check database exists and user has permissions

Issue: "CORS errors in browser console"
Solution:
  - Update CORS_ORIGINS in .env
  - Restart backend server
  - Check frontend is making requests to correct API URL

Issue: "Stripe webhook not receiving events"
Solution:
  - Verify webhook endpoint is publicly accessible
  - Check Stripe dashboard for failed attempts
  - Verify signing secret matches exactly

Issue: "Images not uploading"
Solution:
  - Check upload folder permissions
  - Verify MAX_CONTENT_LENGTH is set correctly
  - Check disk space available

Issue: "Mosaic generation very slow"
Solution:
  - Reduce number of tiles
  - Reduce tile size
  - Optimize image sizes before upload
  - Add more server resources

Issue: "Out of memory during generation"
Solution:
  - Process mosaic asynchronously (Celery)
  - Reduce output dimensions
  - Limit tile folder size

Issue: "Printful orders not syncing"
Solution:
  - Verify API key is correct
  - Check webhook is configured in Printful
  - Look at error logs for specific issues
  - Test with send_to_printful() function
"""

# ============================================================================
# SECURITY CHECKLIST
# ============================================================================

"""
Before going to production:

□ Change all default passwords
□ Set DEBUG=False in production
□ Use strong SECRET_KEY (minimum 32 random characters)
□ Enable HTTPS/SSL
□ Configure CORS properly (whitelist domains only)
□ Validate all user inputs
□ Implement rate limiting on API endpoints
□ Use environment variables for secrets (never commit to git)
□ Set up Web Application Firewall (WAF)
□ Enable CSRF protection on forms
□ Implement proper authentication/authorization
□ Use secure cookies (HttpOnly, Secure, SameSite flags)
□ Regular security audits
□ Keep dependencies updated
□ Backup database regularly
□ Monitor for suspicious activity
□ Implement logging for all important actions
□ Set up error handling (don't leak stack traces)
□ Use parameterized queries (SQLAlchemy handles this)
□ Implement rate limiting on file uploads
□ Scan uploaded files for malware
□ Implement DDOS protection

"""
