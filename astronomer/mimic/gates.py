"""Hard promotion gates (no judgment calls). A change promotes iff ALL pass:
  1. secret-window Brier < base Brier (strictly, on unseen data)
  2. n >= MIN_N (100) — small-n deltas are noise until proven otherwise
  3. frozen copy also beats base (generalization, not just adaptation)
Returns (pass: bool, reasons: list). Stdlib only.
"""
MIN_N = 100


def check_gate(secret_brier, base_brier, frozen_brier, n):
    reasons = []
    if n is None or n < MIN_N:
        reasons.append(f"n={n} < {MIN_N}")
    if secret_brier is None or base_brier is None or not secret_brier < base_brier:
        reasons.append(f"secret {secret_brier} !< base {base_brier}")
    if frozen_brier is None or base_brier is None or not frozen_brier < base_brier:
        reasons.append(f"frozen {frozen_brier} !< base {base_brier}")
    return (not reasons), reasons
