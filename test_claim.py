#!/usr/bin/env python
"""Test script to run fact-check on the GDP claim."""

import json
from dotenv import load_dotenv
from cerebras_fact_checker.factcheck import fact_check_single_claim
from cerebras_fact_checker.clients import create_clients
from cerebras_fact_checker.config import load_settings

load_dotenv()
settings = load_settings()
cerebras_client, parallel_client = create_clients(settings)

claim = "The United States accounts for about 25% of the world's nominal GDP."
result = fact_check_single_claim(
    cerebras_client,
    parallel_client,
    claim=claim,
    model=settings.cerebras_model_name
)

print("\n" + "="*80)
print("RESULT:")
print("="*80)
print(json.dumps(result, indent=2, ensure_ascii=False))
