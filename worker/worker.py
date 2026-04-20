import redis
import time
import os

r = redis.Redis(
    host=os.getenv("REDIS_HOST", "redis"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    password=os.getenv("REDIS_PASSWORD") or None,
    decode_responses=True,
)

QUEUE_KEY = os.getenv("REDIS_QUEUE_KEY", "job")


def process_job(job_id):
    print(f"Processing job {job_id}", flush=True)
    time.sleep(2)
    r.hset(f"job:{job_id}", "status", "completed")
    print(f"Done: {job_id}", flush=True)


while True:
    try:
        job = r.brpop(QUEUE_KEY, timeout=5)
        if job:
            _, job_id = job
            process_job(job_id)
    except redis.exceptions.AuthenticationError as e:
        print(f"Redis auth failed: {e}. Check REDIS_PASSWORD.", flush=True)
        time.sleep(5)
    except redis.exceptions.ConnectionError as e:
        print(f"Redis unavailable: {e}. Retrying in 3s...", flush=True)
        time.sleep(3)
    except Exception as e:
        print(f"Unexpected error: {e}", flush=True)
        time.sleep(3)