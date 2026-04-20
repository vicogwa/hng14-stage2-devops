# FIXES.md

Every bug found in the starter repository, documented with file, line number,
root cause, and exact fix applied.

---

## Fix 1

**File:** `api/main.py`, line 8  
**Issue:** Redis host hardcoded to `"localhost"`. Inside Docker, services
communicate via their Compose service name. `localhost` resolves to the
container's own loopback interface, not the Redis container.  
**Fix:** Replaced with `os.getenv("REDIS_HOST", "redis")`.

---

## Fix 2

**File:** `api/main.py`, line 8  
**Issue:** Redis connection had no password, no env-var config, and no
`decode_responses` flag. The raw client returned bytes on every `hget` call,
requiring manual `.decode()` calls throughout and producing silent failures
when a password-protected Redis instance was used.  
**Fix:** Replaced the static `redis.Redis(host="localhost", port=6379)` call
with a fully env-driven connection:

```python
r = redis.Redis(
    host=os.getenv("REDIS_HOST", "redis"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    password=os.getenv("REDIS_PASSWORD") or None,
    decode_responses=True,
)
```

---

## Fix 3

**File:** `api/main.py`, `get_job` function  
**Issue:** When a job ID did not exist, the endpoint returned HTTP 200 with
`{"error": "not found"}`. This breaks any client that checks `response.status`
or `data.status` — the polling logic in the frontend would receive a 200 with
no `status` key and crash or loop forever.  
**Fix:** Replaced the dict return with a proper HTTP 404:

```python
from fastapi import HTTPException
raise HTTPException(status_code=404, detail="Job not found")
```

---

## Fix 4

**File:** `api/main.py` — missing endpoint  
**Issue:** No `/health` route existed. The Dockerfile `HEALTHCHECK`, the
Compose `healthcheck.test`, and the `depends_on: condition: service_healthy`
chain all rely on this endpoint returning HTTP 200. Without it, the healthcheck
always failed, Redis was never considered healthy, and the entire stack hung
on startup indefinitely.  
**Fix:** Added `/health` route that also validates Redis reachability:

```python
@app.get("/health")
def health():
    try:
        r.ping()
        return {"status": "ok"}
    except Exception:
        return JSONResponse(status_code=503, content={"status": "unavailable"})
```

---

## Fix 5

**File:** `api/main.py` — missing CORS middleware  
**Issue:** No CORS headers were set. Browser-based requests from the frontend
(port 3000) to the API (port 8000) are cross-origin and blocked without
explicit `Access-Control-Allow-Origin` headers.  
**Fix:** Added `CORSMiddleware` driven by an environment variable:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## Fix 6

**File:** `worker/worker.py`, line 3  
**Issue:** Redis host hardcoded to `"localhost"` — same Docker networking
failure as Fix 1. The worker could never connect to the Redis container.  
**Fix:** Replaced with env-var driven connection using the same pattern as the
API, including `decode_responses=True` and password support.

---

## Fix 7

**File:** `worker/worker.py`, lines 1–6  
**Issue:** `import signal` and `import os` were both present. `signal` was
never used anywhere in the file. `os` was also unused because the connection
was hardcoded. Both are F401 violations that fail the flake8 lint stage.  
**Fix:** Removed `import signal`. Retained `import os` as it is now used for
`os.getenv` calls in the env-driven Redis connection.

---

## Fix 8

**File:** `worker/worker.py`, exception handler  
**Issue:** The main loop only caught `redis.exceptions.ConnectionError`. A
Redis `AuthenticationError` — raised when `REDIS_PASSWORD` is missing or
wrong — is a separate exception type. It propagated uncaught, silently
terminating the worker process with exit code 0 and no log output. This was
confirmed by `docker logs` returning empty and `docker inspect` showing exit
code 0 with no error message.  
**Fix:** Added explicit `AuthenticationError` and broad `Exception` catches:

```python
except redis.exceptions.AuthenticationError as e:
    print(f"Redis auth failed: {e}. Check REDIS_PASSWORD.", flush=True)
    time.sleep(5)
except redis.exceptions.ConnectionError as e:
    print(f"Redis unavailable: {e}. Retrying in 3s...", flush=True)
    time.sleep(3)
except Exception as e:
    print(f"Unexpected error: {e}", flush=True)
    time.sleep(3)
```

---

## Fix 9

**File:** `worker/worker.py`, `process_job` function  
**Issue:** `job_id.decode()` was called on the job ID string. With
`decode_responses=True` set on the Redis client, all responses are already
decoded to `str`. Calling `.decode()` on a `str` raises `AttributeError` and
crashes job processing silently.  
**Fix:** Removed `.decode()` — `job_id` is already a plain string.

---

## Fix 10

**File:** `frontend/app.js`, line 5  
**Issue:** `API_URL` hardcoded to `"http://localhost:8000"`. Inside Docker,
the frontend container's `localhost` is its own loopback, not the API
container. All proxied requests to the API failed with connection refused.  
**Fix:**

```javascript
const API_URL = process.env.API_URL || "http://api:8000";
```

---

## Fix 11

**File:** `frontend/app.js` — missing health endpoint  
**Issue:** No `/health` route. The Dockerfile `HEALTHCHECK` and Compose
healthcheck both poll `http://localhost:3000/health`. Without this route,
the frontend was permanently unhealthy and the `depends_on: service_healthy`
condition on downstream services never resolved.  
**Fix:** Added before `app.listen`:

```javascript
app.get('/health', (req, res) => {
  res.status(200).json({ status: 'ok' });
});
```

---

## Fix 12

**File:** `frontend/package.json` — missing `package-lock.json`  
**Issue:** The frontend Dockerfile runs `npm ci`, which requires a
`package-lock.json` with `lockfileVersion >= 1`. No lockfile was committed to
the repository. The Docker build failed immediately at that step with:
`npm error The npm ci command can only install with an existing package-lock.json`.  
**Fix:** Ran `npm install` locally inside `frontend/` to generate
`package-lock.json`, then committed it.

---

## Fix 13

**File:** `frontend/package.json` — missing ESLint devDependency  
**Issue:** The CI pipeline lint stage runs `npx eslint .` in the frontend
directory. ESLint was not listed in `package.json`, so `npm ci` did not
install it, and the lint step failed with command not found.  
**Fix:** Added to `devDependencies`:

```json
"devDependencies": {
  "eslint": "^8.57.0"
}
```

Also added `frontend/.eslintrc.json` with a standard Node.js configuration.

---

## Fix 14

**File:** `worker/Dockerfile` — missing `CMD` instruction  
**Issue:** The final stage of the worker Dockerfile had no `CMD` or
`ENTRYPOINT`. Docker fell back to the base image default from
`python:3.11-slim`, which is `["python3"]` with no script argument. The
Python interpreter launched in non-interactive mode, read EOF from stdin,
and exited cleanly with code 0. The worker never executed a single line of
`worker.py`. Confirmed via:
`docker inspect --format='{{.Config.Cmd}}' hng14-stage2-devops-worker-1`
returning `[python3]`.  
**Fix:** Added as the final line of `worker/Dockerfile`:

```dockerfile
CMD ["python3", "worker.py"]
```

---

## Fix 15

**File:** `worker/Dockerfile`, `HEALTHCHECK` instruction  
**Issue:** The Redis client in the healthcheck command had no socket timeout.
When the connection was slow or auth failed, the client blocked for the full
5-second healthcheck window on every attempt, always registering as a timeout
rather than a clean failure. Nine consecutive timeout failures were confirmed
via `docker inspect .State.Health`.  
**Fix:** Added `socket_connect_timeout=3` and `socket_timeout=3` to the
healthcheck Redis client, ensuring it fails within the 5s window:

```dockerfile
HEALTHCHECK --interval=20s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "\
import redis, os; \
r = redis.Redis(\
    host=os.getenv('REDIS_HOST','redis'), \
    port=int(os.getenv('REDIS_PORT', 6379)), \
    password=os.getenv('REDIS_PASSWORD') or None, \
    socket_connect_timeout=3, \
    socket_timeout=3\
); \
r.ping()" || exit 1
```

---

## Fix 16

**File:** `docker-compose.yml` — Redis started without authentication  
**Issue:** The Redis service had no `command` override. Redis started with no
password enforcement, while the API and worker were configured to send
`REDIS_PASSWORD`. The mismatch caused auth errors on every connection attempt.
The healthcheck also lacked the `-a` flag, causing `redis-cli ping` to return
`NOAUTH` and permanently fail the health check.  
**Fix:** Added `command` and updated `healthcheck.test`:

```yaml
command: redis-server --requirepass ${REDIS_PASSWORD}
healthcheck:
  test: ["CMD-SHELL", "redis-cli -a \"$REDIS_PASSWORD\" ping | grep -q PONG"]
```