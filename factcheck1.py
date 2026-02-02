#!/usr/bin/env python
"""Quick test runner for factcheck.py"""
import sys
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

# Add src to path
repo_root = Path(__file__).parent
src_path = repo_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

# Now import and run
from cerebras_fact_checker.factcheck import fact_check_single_claim
from cerebras_fact_checker.clients import create_clients
from cerebras_fact_checker.config import load_settings

if __name__ == "__main__":
    print("=" * 60)
    print("Cerebras Fact Checker")
    print("=" * 60)
    
    # Initialize clients once
    try:
        settings = load_settings()
        cerebras_client, parallel_client = create_clients(settings)
        model = settings.cerebras_model_name
        print(f"Using model: {model}")
        print(f"Parallel API: {'Configured' if parallel_client else 'Not configured'}")
    except Exception as e:
        print(f"Error initializing clients: {e}")
        sys.exit(1)
    
    while True:
        # Prompt user for claim
        claim = input("\nEnter a claim to fact-check: ").strip()
        
        if not claim:
            print("Error: No claim provided.")
            continue
        
        print("\n" + "=" * 60)
        print("Running fact-checker...")
        print("=" * 60)
        print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] Starting fact-check process...")
        sys.stdout.flush()
        
        try:
            # Use the function directly instead of calling main()
            result = fact_check_single_claim(
                cerebras_client,
                parallel_client,
                claim=claim,
                model=model,
                mode="one-shot",
                num_sources=3,
                reasoning_effort="medium"
            )
            print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] Fact-check process completed")
        except Exception as e:
            print(f"Error during fact-checking: {e}")
        
        # Ask if user wants to check another fact
        another = input("\nWould you like to check another fact? (yes/no): ").strip().lower()
        
        if another not in ['yes', 'y']:
            print("\nThank you for using Cerebras Fact Checker!")
            sys.exit(0)
