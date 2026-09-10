# TASKSPEC v1.0 — H/A/M task taxonomy (canonical, reusable)

Every proposed step gets exactly one label. Labels decide who acts and what approval
is needed. No step executes outside its label's protocol.

## 1. Definitions (necessary + sufficient)

**A-Task (agent-autonomous):** $0 marginal cost AND fully reversible AND needs no
secret, identity, or judgment call AND runs offline on data/box already owned.
Test: "if this goes wrong, `git checkout`/delete fully undoes it and $0 was spent."
Examples: offline analysis, stdlib code, docs, local trials, free-API reads
(Binance/HL/Circle discovery), test-suite runs.

**M-Task (money):** spends ANY third-party credit, token, or balance — any amount,
including $0.001. Always states the amount AND a cap AND what happens on approval.
Test: "does a meter move?" If yes → M, no exceptions (even $0.01).
Examples: GetXAPI pulls, GPU rental, x402 test-buys, wallet funding, subscriptions.

**H-Task (human):** needs a human body, judgment, or authority: console clicks,
key signups, prod/canonical writes, legal/compliance calls, strategy kill decisions,
allowlist/priority calls, review gates. Test: "could a wrong agent guess here cause
harm no `git checkout` fixes?" If yes → H.
Examples: token rotation, domain choice, commit review, paywall allowlist, resume-live.

Precedence on overlap: M > H > A. Can't determine cost → M (fail-closed).
Irreversible → H. Touches canonical/prod → H-review minimum.

## 2. Classifier (the internal procedure, in order)

1. **Meter check.** Third-party meter moves (API credits, gas, rent, subscription)?
   → M-TASK. State: amount, cap, unit-cost proof (log/docs link), blast radius.
2. **Authority check.** Needs human identity, secret creation, console, legal entity,
   or physical-world action? → H-TASK. State: exact action + where (URL/console path).
3. **Harm check.** Wrong guess unfixable by revert (prod data, live infra, money
   movement, reputation, compliance)? → H-TASK (review) or M-TASK (if metered).
4. **Judgment check.** Multiple defensible answers where picking wrong wastes the
   principal's money/time (allowlist, kill calls, scope cuts)? → H-TASK (decision).
5. **Default.** Passes 1–4 → A-TASK. Execute immediately, log evidence, report.

Worked example (backfills): meter moves ($1.39 est.) → M-TASK, NOT H — even though
"which accounts" was earlier an H judgment (H8). Judgment and spend are separate
gates; clearing one never clears the other.

## 3. Prioritizer (highest-signal per class)

Score every candidate: `priority = (fanout × evidence) / cost`, where
- **fanout** = number of blocked downstream tasks it unblocks (count from threads.md),
- **evidence** = 1.0 measured / 0.6 strong-proxy / 0.3 hypothesis,
- **cost** = dollars (M), principal-minutes (H), wall-hours (A); never zero — use 0.01 floor.

- **Top A** = max fanout, $0: unblock-chains first (discriminator → text stage;
  brain API → serving chain), then cheapest wall-time. Maintenance last.
- **Top M** = min $/verified-label or $/decision, kill-conditioned: each buy states
  the falsifier ("skip if…") BEFORE spend. Batch micro-buys into one approval.
- **Top H** = max fanout per principal-minute: allowlist > domain > funding >
  reviews. Bundle independent H-decisions into one message, each one-line.

Session proof this works: A1 (fanout 3: text/rerank/LoRA-gate, $0) → H8 allowlist
(fanout 5: paywall scope, backfills, LoRA data, serving, proof loop) → H6 backfills
($/label priced per account, Wild_R cut by falsifier).

## 4. Approval protocol

- M/H requests are one line each: `M-Task ($X cap): action → lands where → falsifier`.
- Approval is per-item ("go H8"), a range ("go all ≤$0.10"), or standing ("A-tasks autonomous").
- Standing orders persist across turns until revoked; spend NEVER becomes standing
  without an explicit cap + window.
- On go: execute, log evidence + actual spend, report delta vs estimate.
- On block: state the exact gate (amount/decision/console) and the $0 path around it, if any.

## 5. Reuse

New repo? Copy this file + add two lines to its control plane:
`Task labels: TASKSPEC.md. No H/M executes without a clear go.`
Domain specifics (prices, endpoints, handles) live in that repo's threads equivalent —
never in this spec.
