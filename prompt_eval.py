"""
Prompt evaluation entry point.

Usage:
    python prompt_eval.py                     # generate dataset + run eval
    python prompt_eval.py --load              # load saved dataset + run eval
"""
import sys

from dotenv import load_dotenv

load_dotenv()

import os
if not os.getenv("ANTHROPIC_API_KEY"):
    sys.exit("❌  ANTHROPIC_API_KEY not set. Add it to your .env file.")

from utils.dataset  import generate_dataset, save_dataset, load_dataset
from utils.evaluator import run_eval


if __name__ == "__main__":
    use_saved = "--load" in sys.argv

    if use_saved:
        dataset = load_dataset()
        print("Loaded dataset from ./data/tmp/dataset.json")
    else:
        dataset = generate_dataset()
        save_dataset(dataset)

    eval_results = run_eval(dataset)
    # print(json.dumps(eval_results, indent=2))

