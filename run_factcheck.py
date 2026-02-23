import sys
import traceback
from dotenv import load_dotenv

load_dotenv(override=False)

try:
    from cerebras_fact_checker.config import load_settings
    from cerebras_fact_checker.clients import create_clients
    from cerebras_fact_checker.factcheck import fact_check_single_claim

    settings = load_settings()
    cerebras_client, parallel_client = create_clients(settings)

    claim = "At the beginning of the 20th century, the textile industry of the Vosges and the Cevennes regions, in France, declined due to the increasing import of cheaper textile from Asia."

    result = fact_check_single_claim(
        cerebras_client,
        parallel_client,
        claim=claim,
        model=settings.cerebras_model_name,
        num_sources=10,
    )

    print("\n" + "="*60)
    print(f"FINAL VERDICT: {result['verdict'].upper()}")
    print(f"REASON: {result['reason']}")
    print("="*60)

except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    traceback.print_exc()
    sys.exit(1)
