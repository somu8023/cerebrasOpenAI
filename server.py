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
usage_by_ip: dict[str, int] = {}  # IP -> check count

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
    current_usage = usage_by_ip.get(ip, 0)
    
    # Sync with client's local tracker to survive Vercel cold starts
    try:
        local_used = int(request.headers.get('X-Local-Used', '0'))
        if local_used > current_usage:
            current_usage = local_used
            usage_by_ip[ip] = current_usage
    except ValueError:
        pass
    
    if current_usage >= MAX_FREE_CHECKS:
        resp = make_response(jsonify({
            "error": "Rate limit exceeded. You've used all your free fact-checks.",
            "limit_reached": True,
            "used": current_usage,
            "max": MAX_FREE_CHECKS,
            "remaining": 0,
        }), 429)
        return False, resp
    
    return True, None

def increment_usage():
    """Increment usage counter for the current IP."""
    ip = request.remote_addr or 'unknown'
    usage_by_ip[ip] = usage_by_ip.get(ip, 0) + 1
    print(f"[Rate Limit] IP {ip}: {usage_by_ip[ip]}/{MAX_FREE_CHECKS} checks used")

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
        return jsonify({
            "results": results,
            "total_claims": len(results),
            "elapsed_seconds": round(elapsed, 2),
            "model": model,
            "timestamp": datetime.now().isoformat(),
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
    used = usage_by_ip.get(ip, 0)
    
    # Sync with client's local tracker
    try:
        local_used = int(request.headers.get('X-Local-Used', '0'))
        if local_used > used:
            used = local_used
            usage_by_ip[ip] = used
    except ValueError:
        pass

    return jsonify({
        "used": used,
        "max": MAX_FREE_CHECKS,
        "remaining": max(0, MAX_FREE_CHECKS - used),
        "limit_reached": used >= MAX_FREE_CHECKS,
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
