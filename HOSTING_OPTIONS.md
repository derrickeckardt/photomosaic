# Hosting Options Analysis for MosaicStudio

This document provides an analysis of hosting options for the MosaicStudio application, taking into consideration its specific architecture—particularly its backend dependency on the local filesystem for storing uploaded images and generated mosaics.

## ⚠️ Critical Architectural Constraint: Local Filesystem

**Current State:**
The application (`backend_api.py`) stores user uploads and generated mosaics directly on the local disk in the `uploads/` and `mosaics/` directories.
*   **Implication:** Hosting platforms with "ephemeral" filesystems (like standard Heroku dynos, Vercel functions, or AWS Lambda) **cannot** be used directly without data loss. Every time the server restarts or deploys, all user data would be deleted.

**Requirement:**
Any hosting solution chosen **MUST** support persistent storage (Persistent Volumes or "Disk") or a standard Virtual Private Server (VPS) filesystem.

---

## Recommended Options (Ranked by Ease of Maintenance)

### 1. Platform as a Service (PaaS) with Persistent Storage (Recommended)
This balances ease of use (automated deployments, managed SSL, logs) with the requirement for disk storage.

#### **Top Pick: Render (render.com)**
*   **Why:** Offers "Disk" support (persistent storage) for web services. Extremely easy to connect to GitHub for auto-deployments.
*   **Setup:**
    1.  Create a "Web Service" connected to your repo.
    2.  Select Python environment.
    3.  **Crucial Step:** Add a "Disk" (Persistent Volume) in the settings. Mount it to `/opt/render/project/src/uploads` (or wherever your app runs).
    4.  Build Command: `pip install -r requirements.txt`
    5.  Start Command: `gunicorn backend_api:app`
*   **Pros:** Very easy setup, automatic SSL, good UI, affordable.
*   **Cons:** Disks cost extra (~$0.25/GB/month).

#### **Runner Up: Railway (railway.app)**
*   **Why:** Similar to Render, excellent developer experience.
*   **Setup:** Deploy repo, then add a "Volume" to the service and mount it to the upload path.
*   **Pros:** Usage-based pricing, very intuitive interface.

### 2. Virtual Private Server (VPS) - "The Standard Way"
This gives you a full Linux server. It is the most robust option for the current architecture but requires slightly more initial setup.

#### **Providers: DigitalOcean / Hetzner / Linode**
*   **Why:** You have full control over the filesystem. Files stay there until you delete them.
*   **Ease of Deployment:** Moderate (using tools like Docker Compose or CapRover).
*   **Setup Strategy (Docker Compose):**
    1.  Install Docker & Docker Compose on the VPS.
    2.  Create a `docker-compose.yml` in your project.
    3.  Map a volume for data:
        ```yaml
        volumes:
          - ./data/uploads:/app/uploads
          - ./data/mosaics:/app/mosaics
        ```
    4.  Run `docker-compose up -d`.
*   **Pros:** Cheapest for performance, total control, no "ephemeral fs" surprises.
*   **Cons:** You manage security updates, backups, and SSL (though Caddy/Nginx Proxy Manager makes SSL easy).

### 3. Cloud Native (Requires Refactoring) - NOT Recommended yet
*   **Providers:** Heroku (Standard), Vercel, AWS Elastic Beanstalk.
*   **Why:** These platforms are great but require the app to be "stateless".
*   **Refactor Needed:** You would need to rewrite `backend_api.py` to upload files to AWS S3 or Google Cloud Storage instead of `os.path.join(..., 'uploads')`.
*   **Verdict:** Avoid for now unless you plan to scale massively.

---

## Database Considerations

The current app uses **SQLite** (`sqlite:///mosaic_platform.db`).
*   **SQLite** is a file.
*   **On a VPS:** It works fine (stored on disk).
*   **On PaaS (Render/Railway):** You **MUST** ensure the `.db` file is also located on the persistent disk/volume. If it's in the root code directory, it might get reset on deploy.
*   **Production Recommendation:** Even on a VPS, it is better to switch to **PostgreSQL**.
    *   Render/Railway provide managed Postgres with one click.
    *   Change `SQLALCHEMY_DATABASE_URI` env var to the Postgres connection string.

## Final "Ease of Maintenance" Recommendation

**Go with Render.com:**
1.  Connect GitHub repo.
2.  Add a **Disk** mounted to `/var/data` (or similar).
3.  Update `backend_api.py` config to point `UPLOAD_FOLDER` and `SQLALCHEMY_DATABASE_URI` (if using sqlite) to paths inside `/var/data`.
4.  Enjoy automatic deployments and persistent data without managing a Linux server.
