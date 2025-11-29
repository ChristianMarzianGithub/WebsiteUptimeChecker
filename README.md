# Website Uptime Checker

A full-stack uptime checker that measures website availability, response time, SSL health, DNS resolution, redirects, and provides lightweight monitoring with history and alert hooks.

## Features
- **On-demand checks**: HTTP status, response time, redirects, final URL, SSL validity, and DNS records.
- **Monitoring engine**: Background job checks registered URLs every 60 seconds and keeps the latest 20 results per site.
- **History & insights**: Per-URL uptime percentage, UP/DOWN events, and sparkline response chart in the UI.
- **Alert hooks**: Optional webhook notifications on UP/DOWN transitions (configure `ALERT_WEBHOOK_URL`).
- **Responsive UI**: React + Tailwind with dark/light toggle, loading states, and error handling.

## Project Structure
```
backend/     # FastAPI service, monitoring engine, tests, Dockerfile
frontend/    # React + Vite + Tailwind SPA, Dockerfile
docker-compose.yml
```

## Backend (FastAPI)
### Setup
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Endpoints
- `GET /check?url=`: Run a live uptime + DNS + SSL check.
- `GET /monitor/list`: List monitored URLs with last status and uptime %.
- `POST /monitor/add?url=`: Add URL to monitoring list.
- `DELETE /monitor/remove?url=`: Remove URL from monitoring.
- `GET /monitor/history?url=`: Last 20 checks for a URL.
- `GET /health`: Service health.

Monitoring runs every 60 seconds and stores data in `monitoring_data.json` (or in-memory if the file is absent). Webhook alerts fire when status changes UP/DOWN if `ALERT_WEBHOOK_URL` is set.

### Tests
```bash
cd backend
pytest
```

## Frontend (React + Vite + Tailwind)
### Setup
```bash
cd frontend
npm install
npm run dev -- --host --port 5173
```

Set `VITE_API_URL` to point to the backend (defaults to `http://localhost:8000`).

## Docker
### Backend image
```bash
cd backend
docker build -t uptime-backend .
```

### Frontend image
```bash
cd frontend
docker build -t uptime-frontend .
```

### Compose (local development)
```bash
docker-compose up --build
```
Frontend on `http://localhost:5173`, backend on `http://localhost:8000`.

## Cloud Run Deployment
1. Build and push images:
   ```bash
   gcloud builds submit --tag gcr.io/PROJECT_ID/uptime-backend ./backend
   gcloud builds submit --tag gcr.io/PROJECT_ID/uptime-frontend ./frontend
   ```
2. Deploy services:
   ```bash
   gcloud run deploy uptime-backend --image gcr.io/PROJECT_ID/uptime-backend --platform managed --region REGION --allow-unauthenticated
   gcloud run deploy uptime-frontend --image gcr.io/PROJECT_ID/uptime-frontend --platform managed --region REGION --allow-unauthenticated --set-env-vars VITE_API_URL=https://BACKEND_URL
   ```

## Alerts
Set `ALERT_WEBHOOK_URL` in the backend environment to POST JSON payloads when a monitored site goes DOWN or back UP:
```json
{
  "url": "https://example.com",
  "status": "DOWN",
  "timestamp": "2025-01-01T12:22:55Z",
  "status_code": 500
}
```

## Limitations
- The monitoring store defaults to a JSON file for simplicity; swap with a database if needed.
- Network access is required for dependency installation and live checks.
