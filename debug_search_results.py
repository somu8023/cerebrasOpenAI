import json
from cerebras_fact_checker.config import load_settings
from cerebras_fact_checker.clients import create_clients
from cerebras_fact_checker.factcheck import fact_check_single_claim

claim = "At the beginning of the 20th century, the textile industry of the Vosges and the Cevennes regions, in France, declined due to the increasing import of cheaper textile from Asia."
from dotenv import load_dotenv
load_dotenv()
s = load_settings()
c, p = create_clients(s)

result = fact_check_single_claim(c, p, claim=claim, model=s.cerebras_model_name)

with open('debug_search_results.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, indent=2)
