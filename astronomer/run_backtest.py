"""Full backtest pipeline runner."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


def main():
    """Run full pipeline: collect calls → fetch prices → backtest → reputation."""
    print("="*60)
    print("FULL BACKTEST PIPELINE")
    print("="*60)

    # Step 1: Collect historical calls
    print("\n--- STEP 1: Collect Historical Calls ---")
    from collect_calls import main as collect_main
    collect_main()

    # Step 2: Fetch price data
    print("\n--- STEP 2: Fetch Price Data ---")
    from price_data import main as price_main
    price_main()

    # Step 3: Run backtest
    print("\n--- STEP 3: Run Backtest ---")
    from backtest import main as backtest_main
    backtest_main()

    print("\n" + "="*60)
    print("PIPELINE COMPLETE")
    print("="*60)


if __name__ == "__main__":
    main()
