"""Pump.fun transaction fetcher — fetch and decode Pump transactions from Solana RPC.

Uses public Solana RPC (free, rate-limited) to fetch Pump transactions.
No Helius key needed for basic functionality.

Usage:
    python pump_indexer.py --fetch august    # Fetch August Pump transactions
    python pump_indexer.py --decode          # Decode fetched transactions
    python pump_indexer.py --status          # Show index status
"""

import argparse
import json
import struct
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import httpx

# Pump.fun program IDs (from pump-public-docs/idl/)
PUMPFUN_PROGRAM_ID = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"
PUMPSWAP_PROGRAM_ID = "pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA"

# Pump.fun IDL instruction discriminators (from pump-public-docs)
# These are the first 8 bytes of the instruction hash
PUMP_INSTRUCTIONS = {
    b'\xc3\xcf\x1c\x13\x85\x21\x0e\x01': 'create',      # create_simple_token
    b'\x18\x1e\xc8\x28\x05\x1c\x07\x17': 'buy',
    b'\x66\x06\x3d\x12\x01\xd5\x53\x08': 'sell',
    b'\x04\x07\x33\x04\x0f\x0e\x0e\x95': 'withdraw',    # withdraw_from_bonding_curve
}


class PumpTransactionFetcher:
    """Fetch Pump.fun transactions from Solana RPC."""

    def __init__(self, rpc_url: str = "https://api.mainnet-beta.solana.com"):
        self.rpc_url = rpc_url
        self.client = httpx.Client(timeout=30.0)
        self._last_request = 0.0

    def _rate_limit(self):
        """Rate limit to ~10 req/s for public RPC."""
        elapsed = time.time() - self._last_request
        if elapsed < 0.1:
            time.sleep(0.1 - elapsed)
        self._last_request = time.time()

    def _rpc_call(self, method: str, params: list) -> dict:
        """Make an RPC call."""
        self._rate_limit()
        resp = self.client.post(self.rpc_url, json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params,
        })
        return resp.json()

    def get_signatures_for_address(self, address: str, before: Optional[str] = None,
                                    limit: int = 1000) -> list[dict]:
        """Get transaction signatures for a program address."""
        params = [address, {"limit": limit}]
        if before:
            params[1]["before"] = before

        result = self._rpc_call("getSignaturesForAddress", params)
        return result.get("result", [])

    def get_transaction(self, signature: str) -> Optional[dict]:
        """Get a parsed transaction by signature."""
        result = self._rpc_call("getTransaction", [
            signature,
            {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}
        ])
        return result.get("result")

    def fetch_pump_transactions(self, start_date: str, end_date: str,
                                 max_transactions: int = 1000) -> list[dict]:
        """Fetch Pump.fun transactions in a date range.

        Args:
            start_date: YYYY-MM-DD
            end_date: YYYY-MM-DD
            max_transactions: Maximum transactions to fetch

        Returns:
            List of decoded Pump transactions
        """
        start_dt = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)

        all_transactions = []
        before = None
        page = 0

        print(f"Fetching Pump transactions from {start_date} to {end_date}...")

        while len(all_transactions) < max_transactions:
            page += 1
            sigs = self.get_signatures_for_address(PUMPFUN_PROGRAM_ID, before=before)

            if not sigs:
                break

            for sig_info in sigs:
                sig = sig_info.get("signature", "")
                block_time = sig_info.get("blockTime")

                if not block_time:
                    continue

                tx_time = datetime.fromtimestamp(block_time, tz=timezone.utc)

                # Check date range
                if tx_time < start_dt:
                    # Past our range, we're done
                    print(f"  Reached {tx_time.strftime('%Y-%m-%d'), stopping}")
                    return all_transactions

                if tx_time > end_dt:
                    continue

                # Fetch full transaction
                tx = self.get_transaction(sig)
                if tx and not tx.get("meta", {}).get("err"):
                    decoded = self._decode_pump_transaction(tx, sig, block_time)
                    if decoded:
                        all_transactions.append(decoded)

                if len(all_transactions) % 100 == 0 and all_transactions:
                    print(f"  Fetched {len(all_transactions)} decoded transactions...")

            before = sigs[-1].get("signature")
            time.sleep(0.5)

        print(f"  Total: {len(all_transactions)} decoded transactions")
        return all_transactions

    def _decode_pump_transaction(self, tx: dict, sig: str, block_time: int) -> Optional[dict]:
        """Decode a Pump.fun transaction into structured data."""
        try:
            meta = tx.get("meta", {})
            transaction = tx.get("transaction", {})
            message = transaction.get("message", {})

            # Get account keys
            account_keys = message.get("accountKeys", [])
            if isinstance(account_keys[0], dict):
                account_keys = [k.get("pubkey", k) for k in account_keys]

            # Find Pump program in instructions
            instructions = message.get("instructions", [])
            inner_instructions = meta.get("innerInstructions", [])

            # Check all instructions for Pump program
            all_ixs = instructions + [
                ix for inner in inner_instructions
                for ix in inner.get("instructions", [])
            ]

            pump_ix = None
            for ix in all_ixs:
                program_id = ix.get("programId", "")
                if program_id in (PUMPFUN_PROGRAM_ID, PUMPSWAP_PROGRAM_ID):
                    pump_ix = ix
                    break

            if not pump_ix:
                return None

            # Parse instruction data
            data = pump_ix.get("data", "")
            if not data:
                return None

            # Try to decode the instruction type
            import base64
            try:
                raw_data = base64.b64decode(data)
            except:
                return None

            if len(raw_data) < 8:
                return None

            discriminator = raw_data[:8]
            ix_type = "unknown"
            for disc, name in PUMP_INSTRUCTIONS.items():
                if discriminator == disc:
                    ix_type = name
                    break

            # Parse accounts
            accounts = pump_ix.get("accounts", [])

            # Extract basic info
            result = {
                "signature": sig,
                "block_time": block_time,
                "timestamp": datetime.fromtimestamp(block_time, tz=timezone.utc).isoformat(),
                "program_id": pump_ix.get("programId", ""),
                "instruction_type": ix_type,
                "accounts": accounts,
                "data_length": len(raw_data),
            }

            # Try to extract token mint from accounts
            # Pump.fun account layout: [program, bonding_curve, associated_bonding_curve, user, associated_user, token_program, rent, system_program, ...]
            if len(accounts) >= 4:
                result["token_account"] = accounts[1] if len(accounts) > 1 else None
                result["user"] = accounts[3] if len(accounts) > 3 else None

            # Parse buy/sell amounts if possible
            if ix_type in ("buy", "sell") and len(raw_data) >= 24:
                try:
                    # Buy: discriminator(8) + amount(8) + max_sol_cost(8)
                    # Sell: discriminator(8) + amount(8) + min_sol_output(8)
                    amount = struct.unpack('<Q', raw_data[8:16])[0]
                    sol_amount = struct.unpack('<Q', raw_data[16:24])[0]
                    result["token_amount"] = amount
                    result["sol_lamports"] = sol_amount
                    result["sol_amount"] = sol_amount / 1e9
                except:
                    pass

            return result

        except Exception as e:
            return None

    def close(self):
        self.client.close()


def save_transactions(txs: list[dict], path: Path):
    """Save transactions to JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(txs, f, indent=2)
    print(f"Saved {len(txs)} transactions to {path}")


def main():
    parser = argparse.ArgumentParser(description='Pump.fun transaction fetcher')
    parser.add_argument('--fetch', nargs=2, metavar=('START', 'END'),
                        help='Fetch transactions for date range (YYYY-MM-DD)')
    parser.add_argument('--rpc', default='https://api.mainnet-beta.solana.com',
                        help='Solana RPC URL')
    parser.add_argument('--max', type=int, default=1000,
                        help='Max transactions to fetch')
    parser.add_argument('--output', type=str,
                        help='Output file path')
    args = parser.parse_args()

    if args.fetch:
        fetcher = PumpTransactionFetcher(args.rpc)
        txs = fetcher.fetch_pump_transactions(
            args.fetch[0], args.fetch[1], args.max
        )

        if args.output:
            out_path = Path(args.output)
        else:
            out_path = Path(f"data/pump_transactions_{args.fetch[0]}_{args.fetch[1]}.json")

        save_transactions(txs, out_path)
        fetcher.close()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
