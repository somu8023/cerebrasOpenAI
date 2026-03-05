#!/usr/bin/env python
"""Flask API server for the Cerebras Fact Checker frontend."""

import sys
import os

# Force UTF-8 on Windows to handle Unicode in LLM responses
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
import json
import time
import traceback
from pathlib import Path
from datetime import datetime

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
repo_root = Path(__file__).parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from cerebras_fact_checker.factcheck import fact_check_single_claim, fact_check_text
from cerebras_fact_checker.clients import create_clients
from cerebras_fact_checker.config import load_settings

app = Flask(__name__, static_folder='frontend', static_url_path='')
CORS(app)

# Initialize clients once at startup
settings = None
cerebras_client = None
parallel_client = None
model = None

# ---- Soft Launch: Server-Side Rate Limiting ----
MAX_FREE_CHECKS = int(os.getenv('MAX_FREE_CHECKS', 5))
SUPERUSER_SECRET = os.getenv('SUPERUSER_SECRET', 'cerebras2024')

# In-memory fallback (used when Redis is not configured, e.g. local dev)
_mem_usage: dict[str, dict] = {}  # IP -> {"count": int, "date": "YYYY-MM-DD"}

# ---- Redis (Upstash) client ----
_redis_client = None

def _get_redis():
    """Return an Upstash Redis client if env vars are present, else None."""
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    url = os.getenv('UPSTASH_REDIS_REST_URL')
    token = os.getenv('UPSTASH_REDIS_REST_TOKEN')
    if url and token:
        try:
            from upstash_redis import Redis
            _redis_client = Redis(url=url, token=token)
            print("[Rate Limit] Using Upstash Redis for persistent quota tracking.")
        except Exception as e:
            print(f"[Rate Limit] Redis init failed, falling back to in-memory: {e}")
    else:
        print("[Rate Limit] UPSTASH_REDIS_REST_URL/TOKEN not set — using in-memory fallback.")
    return _redis_client


def _today_utc() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d")


def _next_midnight_utc() -> str:
    """ISO 8601 string for the next UTC midnight."""
    from datetime import timedelta
    now = datetime.utcnow()
    next_mid = datetime(now.year, now.month, now.day) + timedelta(days=1)
    return next_mid.strftime("%Y-%m-%dT%H:%M:%SZ")


def _seconds_until_midnight() -> int:
    """Seconds remaining until next UTC midnight (+ 60s buffer)."""
    from datetime import timedelta
    now = datetime.utcnow()
    midnight = datetime(now.year, now.month, now.day) + timedelta(days=1)
    return int((midnight - now).total_seconds()) + 60


def _redis_key(ip: str) -> str:
    return f"ratelimit:{ip}:{_today_utc()}"


def _get_count_redis(ip: str) -> int:
    """Get today's usage count for an IP from Redis."""
    r = _get_redis()
    if r is None:
        return 0
    try:
        val = r.get(_redis_key(ip))
        return int(val) if val is not None else 0
    except Exception as e:
        print(f"[Rate Limit] Redis GET error: {e}")
        return 0


def _set_count_redis(ip: str, count: int):
    """Set today's usage count for an IP in Redis with a TTL until next midnight."""
    r = _get_redis()
    if r is None:
        return
    try:
        key = _redis_key(ip)
        ttl = _seconds_until_midnight()
        r.set(key, count, ex=ttl)
    except Exception as e:
        print(f"[Rate Limit] Redis SET error: {e}")


def _incr_redis(ip: str) -> int:
    """Atomically increment today's usage count and return the new value."""
    r = _get_redis()
    if r is None:
        return 0
    try:
        key = _redis_key(ip)
        new_val = r.incr(key)
        # Set TTL only on first increment (when key was just created)
        if new_val == 1:
            r.expire(key, _seconds_until_midnight())
        return new_val
    except Exception as e:
        print(f"[Rate Limit] Redis INCR error: {e}")
        return 0


# ---- Fallback in-memory helpers ----

def _get_count_mem(ip: str) -> tuple[int, bool]:
    """Returns (current_count, had_existing_record_today)."""
    today = _today_utc()
    record = _mem_usage.get(ip)
    if record and record.get("date") == today:
        return record["count"], True
    _mem_usage[ip] = {"count": 0, "date": today}
    return 0, False


def _set_count_mem(ip: str, count: int):
    today = _today_utc()
    _mem_usage[ip] = {"count": count, "date": today}


def _incr_mem(ip: str) -> int:
    today = _today_utc()
    record = _mem_usage.get(ip)
    if record is None or record.get("date") != today:
        record = {"count": 0, "date": today}
        _mem_usage[ip] = record
    record["count"] += 1
    return record["count"]


def check_rate_limit():
    """Check if the current request is within rate limits.
    Returns (allowed: bool, response_or_none).
    When allowed=False, response is a ready-to-return Flask response with status 429.
    """
    from flask import make_response
    # Superuser bypass via secret header
    if request.headers.get('X-Superuser') == SUPERUSER_SECRET:
        return True, None

    ip = request.remote_addr or 'unknown'
    redis = _get_redis()

    if redis is not None:
        # --- Redis path ---
        current_usage = _get_count_redis(ip)
    else:
        # --- In-memory fallback path ---
        current_usage, _ = _get_count_mem(ip)

    reset_at_utc = _next_midnight_utc()

    if current_usage >= MAX_FREE_CHECKS:
        resp = make_response(jsonify({
            "error": "Rate limit exceeded. You've used all your free fact-checks.",
            "limit_reached": True,
            "used": current_usage,
            "max": MAX_FREE_CHECKS,
            "remaining": 0,
            "reset_at_utc": reset_at_utc,
        }), 429)
        return False, resp

    return True, None


def increment_usage():
    """Increment usage counter for the current IP."""
    ip = request.remote_addr or 'unknown'
    redis = _get_redis()
    if redis is not None:
        new_count = _incr_redis(ip)
    else:
        new_count = _incr_mem(ip)
    print(f"[Rate Limit] IP {ip}: {new_count}/{MAX_FREE_CHECKS} checks used (UTC {_today_utc()})")

def init_clients():
    global settings, cerebras_client, parallel_client, model
    settings = load_settings()
    cerebras_client, parallel_client = create_clients(settings)
    model = settings.cerebras_model_name
    print(f"[Server] Initialized with model: {model}")

try:
    init_clients()
except Exception as e:
    print(f"[Server] Warning: Could not initialize clients at startup: {e}")


@app.route('/')
def serve_frontend():
    return send_from_directory('frontend', 'index.html')


@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('frontend', path)


@app.route('/api/fact-check', methods=['POST'])
def api_fact_check():
    """Fact-check a single claim."""
    global cerebras_client, parallel_client, model

    if not cerebras_client or not parallel_client:
        try:
            init_clients()
        except Exception as e:
            return jsonify({"error": f"Failed to initialize API clients: {str(e)}"}), 500

    # Server-side rate limit check
    allowed, response = check_rate_limit()
    if not allowed:
        return response

    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON body provided"}), 400

    claim = data.get('claim', '').strip()
    if not claim:
        return jsonify({"error": "No claim provided"}), 400

    start_time = time.time()

    try:
        result = fact_check_single_claim(
            cerebras_client,
            parallel_client,
            claim=claim,
            model=model,
        )
        elapsed = time.time() - start_time
        result['elapsed_seconds'] = round(elapsed, 2)
        result['model'] = model
        result['timestamp'] = datetime.now().isoformat()
        result['reset_at_utc'] = _next_midnight_utc()
        increment_usage()
        return jsonify(result)

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/api/fact-check-text', methods=['POST'])
def api_fact_check_text():
    """Extract claims from text and fact-check them all."""
    global cerebras_client, parallel_client, model

    if not cerebras_client or not parallel_client:
        try:
            init_clients()
        except Exception as e:
            return jsonify({"error": f"Failed to initialize API clients: {str(e)}"}), 500

    # Server-side rate limit check
    allowed, response = check_rate_limit()
    if not allowed:
        return response

    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON body provided"}), 400

    text = data.get('text', '').strip()
    if not text:
        return jsonify({"error": "No text provided"}), 400

    max_claims = int(data.get('max_claims', 6))

    start_time = time.time()

    try:
        results = fact_check_text(
            cerebras_client,
            parallel_client,
            text=text,
            model=model,
            max_claims=max_claims,
        )
        elapsed = time.time() - start_time
        increment_usage()
        return jsonify({
            "results": results,
            "total_claims": len(results),
            "elapsed_seconds": round(elapsed, 2),
            "model": model,
            "timestamp": datetime.now().isoformat(),
            "reset_at_utc": _next_midnight_utc(),
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/api/usage', methods=['GET'])
def get_usage():
    """Check remaining usage for the current IP."""
    # Superuser check
    if request.headers.get('X-Superuser') == SUPERUSER_SECRET:
        return jsonify({"superuser": True, "unlimited": True})

    ip = request.remote_addr or 'unknown'
    redis = _get_redis()

    if redis is not None:
        # --- Redis path ---
        used = _get_count_redis(ip)
    else:
        # --- In-memory fallback ---
        used, _ = _get_count_mem(ip)

    return jsonify({
        "used": used,
        "max": MAX_FREE_CHECKS,
        "remaining": max(0, MAX_FREE_CHECKS - used),
        "limit_reached": used >= MAX_FREE_CHECKS,
        "reset_at_utc": _next_midnight_utc(),
    })


@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({
        "status": "ok",
        "model": model,
        "clients_initialized": cerebras_client is not None and parallel_client is not None,
    })


@app.route('/api/version', methods=['GET'])
def get_version():
    """Return the current git commit hash for display in the UI."""
    import subprocess
    try:
        sha = subprocess.check_output(
            ['git', 'rev-parse', '--short', 'HEAD'],
            cwd=str(repo_root),
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except Exception:
        sha = 'unknown'
    return jsonify({"commit": sha})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
