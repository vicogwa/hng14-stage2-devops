# Job Processing System

A containerized microservices application: a Node.js frontend, a Python/FastAPI
backend, a Python worker, and Redis — all orchestrated with Docker Compose.

Users submit jobs through the frontend. The API writes the job to Redis. The
worker picks it up, processes it, and updates its status. The frontend polls
until the job completes.

---

## Prerequisites

Install the following on your machine before proceeding:

- **Docker** >= 24.0 — https://docs.docker.com/get-docker/
- **Docker Compose plugin** >= 2.20 (included with Docker Desktop)
- **Git**

Verify:

```bash
docker --version
docker compose version
git --version
```

---

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/vicogwa/hng14-stage2-devops.git
cd hng14-stage2-devops
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and set a value for `REDIS_PASSWORD`. All other defaults work
out of the box for local development.

```env
REDIS_PASSWORD=your_strong_password_here
```

Do not commit `.env`. It is listed in `.gitignore`.

### 3. Start the stack

```bash
docker compose up -d --build --wait
```

This builds all three images, starts Redis first, waits for it to become
healthy, then starts the API and worker, then the frontend. The `--wait` flag
blocks until every service passes its healthcheck.

---

## Verify the Stack

```bash
docker compose ps
```

Expected output — all four services show `healthy`:
NAME                              STATUS
hng14-stage2-devops-redis-1       healthy
hng14-stage2-devops-api-1         healthy
hng14-stage2-devops-worker-1      healthy
hng14-stage2-devops-frontend-1    healthy

Open http://localhost:3000 in a browser. Click **Submit New Job**. The job
should transition from `queued` → `completed` within a few seconds.

---

## Manual Integration Check

Submit a job from the command line and poll until it completes:

```bash
# Submit
RESPONSE=$(curl -s -X POST http://localhost:3000/submit)
echo $RESPONSE

# Copy the job_id value from the response, then:
curl -s http://localhost:3000/status/<job_id>

# Run again after ~5 seconds
curl -s http://localhost:3000/status/<job_id>
# {"job_id":"...","status":"completed"}
```

---

## View Logs

```bash
docker compose logs -f             # all services
docker compose logs -f worker      # worker only
docker compose logs -f api         # API only
```

---

## Run Unit Tests Locally

```bash
pip install -r api/requirements.txt
pytest api/tests/ --cov=api -v
```

---

## Stop the Stack

```bash
docker compose down -v
```

The `-v` flag removes the named volumes. Omit it if you want Redis data to
persist across restarts.

---

## Port Reference

| Service  | Host Port | Notes                        |
|----------|-----------|------------------------------|
| Frontend | 3000      | Configurable via FRONTEND_PORT |
| API      | —         | Internal only (no host port) |
| Redis    | —         | Internal only (no host port) |

---

## CI/CD Pipeline

The GitHub Actions pipeline runs on every push. Stages run in strict order:
lint → test → build → security scan → integration test → deploy

- **lint** — flake8 (Python), ESLint (JavaScript), hadolint (Dockerfiles)
- **test** — pytest with Redis mocked, coverage report uploaded as artifact
- **build** — images built and pushed to an ephemeral local registry, tagged
  with git SHA and `latest`
- **security scan** — Trivy scans all three images, fails on CRITICAL findings,
  uploads SARIF results as artifact
- **integration test** — full stack starts inside the runner, a job is
  submitted and polled to completion, stack torn down regardless of outcome
- **deploy** — runs on `main` branch pushes only; performs a scripted rolling
  update with a 60-second health check window before cutting over

The deploy stage requires three GitHub Actions Secrets to be configured:
`DEPLOY_HOST`, `DEPLOY_USER`, and `DEPLOY_SSH_KEY`.