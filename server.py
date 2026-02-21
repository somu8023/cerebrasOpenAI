#!/usr/bin/env python
"""Flask API server for the Cerebras Fact Checker frontend."""

import sys
import os
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
usage_by_ip: dict[str, dict] = {}  # IP -> {"count": int, "date": "YYYY-MM-DD"}
_request_count = 0  # for periodic stale-IP cleanup


def _today_utc() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d")


def _next_midnight_utc() -> str:
    """ISO 8601 string for the next UTC midnight."""
    from datetime import timedelta
    now = datetime.utcnow()
    next_mid = datetime(now.year, now.month, now.day) + timedelta(days=1)
    return next_mid.strftime("%Y-%m-%dT%H:%M:%SZ")


def _cleanup_stale_ips():
    today = _today_utc()
    stale = [ip for ip, rec in usage_by_ip.items() if rec.get("date", "") < today]
    for ip in stale:
        del usage_by_ip[ip]
    if stale:
        print(f"[Rate Limit] Cleaned up {len(stale)} stale IP records")


def check_rate_limit():
    """Check if the current request is within rate limits.
    Returns (allowed: bool, response_or_none).
    When allowed=False, response is a ready-to-return Flask response with status 429.
    """
    global _request_count
    from flask import make_response
    # Superuser bypass via secret header
    if request.headers.get('X-Superuser') == SUPERUSER_SECRET:
        return True, None

    ip = request.remote_addr or 'unknown'
    today = _today_utc()

    # Periodic cleanup every 100 requests
    _request_count += 1
    if _request_count % 100 == 0:
        _cleanup_stale_ips()

    # Get or initialize record; reset automatically on new UTC day
    record = usage_by_ip.get(ip)
    if record is None or record.get("date") != today:
        record = {"count": 0, "date": today}
        usage_by_ip[ip] = record

    current_usage = record["count"]

    # Sync with client's local tracker (only meaningful on same UTC day)
    try:
        local_used = int(request.headers.get('X-Local-Used', '0'))
        if local_used > current_usage:
            current_usage = local_used
            record["count"] = current_usage
    except ValueError:
        pass

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
    today = _today_utc()
    record = usage_by_ip.get(ip)
    if record is None or record.get("date") != today:
        record = {"count": 0, "date": today}
        usage_by_ip[ip] = record
    record["count"] += 1
    print(f"[Rate Limit] IP {ip}: {record['count']}/{MAX_FREE_CHECKS} checks used (UTC {today})")

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

    mode = data.get('mode', 'one-shot')
    num_sources = int(data.get('num_sources', 3))
    reasoning_effort = data.get('reasoning_effort', 'medium')

    start_time = time.time()

    try:
        result = fact_check_single_claim(
            cerebras_client,
            parallel_client,
            claim=claim,
            model=model,
            mode=mode,
            num_sources=num_sources,
            reasoning_effort=reasoning_effort,
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
    mode = data.get('mode', 'one-shot')
    num_sources = int(data.get('num_sources', 3))
    reasoning_effort = data.get('reasoning_effort', 'medium')

    start_time = time.time()

    try:
        results = fact_check_text(
            cerebras_client,
            parallel_client,
            text=text,
            model=model,
            max_claims=max_claims,
            mode=mode,
            num_sources=num_sources,
            reasoning_effort=reasoning_effort,
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
    today = _today_utc()
    record = usage_by_ip.get(ip)

    # Reset if new UTC day
    if record is None or record.get("date") != today:
        record = {"count": 0, "date": today}
        usage_by_ip[ip] = record

    used = record["count"]

    # Sync with client's local tracker (same day only)
    try:
        local_used = int(request.headers.get('X-Local-Used', '0'))
        if local_used > used:
            used = local_used
            record["count"] = used
    except ValueError:
        pass

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


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
