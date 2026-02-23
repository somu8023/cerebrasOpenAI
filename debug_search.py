from cerebras_fact_checker.search import generate_search_variations
import json

claim = "At the beginning of the 20th century, the textile industry of the Vosges and the Cevennes regions, in France, declined due to the increasing import of cheaper textile from Asia."
queries = generate_search_variations(claim)
print(json.dumps(queries, indent=2))
