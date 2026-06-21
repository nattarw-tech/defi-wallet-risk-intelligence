import pandas as pd
from datetime import datetime, timezone


def analyse_wallet(account_info: dict, transactions: list) -> dict:
    score = 0
    flags = []

    # ── Guard: if we have no data, return a neutral result ──────────────────
    if not account_info or not transactions:
        return {
            "score": 0,
            "level": "Unknown",
            "flags": ["Insufficient data to assess risk"],
            "stats": {}
        }

    # ── Parse transactions into a Pandas DataFrame ───────────────────────────
    rows = []
    for tx in transactions:
        tx_json = tx.get("tx_json", {})
        rows.append({
            "type": tx_json.get("TransactionType", "Unknown"),
            "hash": tx.get("hash", ""),
            "timestamp": tx.get("close_time_iso", ""),
            "amount_raw": tx_json.get("Amount", None),
            "destination": tx_json.get("Destination", ""),
            "account": tx_json.get("Account", ""),
            "fee": int(tx_json.get("Fee", 0)) / 1_000_000  # convert drops to XRP
        })

    df = pd.DataFrame(rows)

    # ── Basic statistics we will use for scoring and display ─────────────────
    total_txns = len(df)
    unique_counterparties = _count_unique_counterparties(df)
    payment_count = len(df[df["type"] == "Payment"])
    payment_ratio = payment_count / total_txns if total_txns > 0 else 0
    lifetime_txns = int(account_info.get("Sequence", 0))
    balance_xrp = int(account_info.get("Balance", 0)) / 1_000_000

    # ── SIGNAL 1: Transaction Velocity (max 30 points) ───────────────────────
    # I fetched 50 transactions. If timestamps are available, I check how
    # compressed they are in time. Many transactions in a very short window
    # is a classic layering indicator.
    velocity_score, velocity_flag = _score_velocity(df)
    score += velocity_score
    if velocity_flag:
        flags.append(velocity_flag)

    # ── SIGNAL 2: Counterparty Diversity (max 25 points) ─────────────────────
    # Too many unique counterparties in a small sample suggests the wallet
    # is dispersing funds to many different destinations — a layering pattern.
    if unique_counterparties >= 40:
        score += 25
        flags.append(f"Extreme counterparty diversity: {unique_counterparties} unique addresses in last {total_txns} transactions")
    elif unique_counterparties >= 25:
        score += 15
        flags.append(f"High counterparty diversity: {unique_counterparties} unique addresses in last {total_txns} transactions")
    elif unique_counterparties >= 15:
        score += 8

    # ── SIGNAL 3: Payment Concentration (max 20 points) ──────────────────────
    # A wallet that is almost exclusively Payments (>85%) with very high volume
    # looks like a pass-through account, funds come in and immediately go out.
    if payment_ratio > 0.85 and total_txns >= 20:
        score += 20
        flags.append(f"Pass-through pattern: {payment_ratio:.0%} of transactions are Payments")
    elif payment_ratio > 0.70 and total_txns >= 10:
        score += 10

    # ── SIGNAL 4: Account Age vs Activity (max 25 points) ────────────────────
    # Sequence number on XRPL is a lifetime transaction counter.
    # A wallet with a very high sequence number but very low XRP balance
    # has been extremely active but holds almost nothing — suspicious.
    if lifetime_txns > 50_000_000 and balance_xrp < 20:
        score += 25
        flags.append(f"EXTREME volume low-balance account: {lifetime_txns:,} lifetime transactions, only {balance_xrp:.2f} XRP held — likely automated or exchange routing wallet")
    elif lifetime_txns > 1_000_000 and balance_xrp < 50:
        score += 25
        flags.append(f"High-volume low-balance account: {lifetime_txns:,} lifetime transactions, only {balance_xrp:.2f} XRP held")
    elif lifetime_txns > 100_000 and balance_xrp < 20:
        score += 15
        flags.append(f"Elevated activity relative to balance: {lifetime_txns:,} lifetime transactions")
    elif lifetime_txns > 10_000 and balance_xrp < 10:
        score += 8

    # ── Cap score at 100 ─────────────────────────────────────────────────────
    score = min(score, 100)

    # ── Determine risk level from score ──────────────────────────────────────
    level = _score_to_level(score)

    # ── Return the full result ────────────────────────────────────────────────
    return {
        "score": score,
        "level": level,
        "flags": flags if flags else ["No significant risk indicators detected"],
        "stats": {
            "total_transactions_analysed": total_txns,
            "unique_counterparties": unique_counterparties,
            "payment_ratio": round(payment_ratio, 3),
            "lifetime_transactions": lifetime_txns,
            "balance_xrp": round(balance_xrp, 2),
            "transaction_types": df["type"].value_counts().to_dict()
        }
    }


# ── Helper functions ──────────────────────────────────────────────────────────

def _count_unique_counterparties(df: pd.DataFrame) -> int:
    """Counts the number of unique wallet addresses this wallet interacted with."""
    # Collect all non-empty destination and account addresses, excluding blanks
    counterparties = set()
    for addr in df["destination"].tolist() + df["account"].tolist():
        if addr and len(addr) > 10:  # basic check it looks like an address
            counterparties.add(addr)
    return len(counterparties)


def _score_velocity(df: pd.DataFrame) -> tuple:
    """
    Scores transaction velocity based on time compression.
    If timestamps are available, checks how many transactions occurred within a 24-hour window.
    Returns a (score, flag_message_or_None) tuple.
    """
    timestamps = df["timestamp"].dropna()
    timestamps = timestamps[timestamps != ""]

    if len(timestamps) < 5:
        return 0, None

    try:
        # Parse ISO timestamps into datetime objects
        parsed = pd.to_datetime(timestamps, utc=True)
        time_range_hours = (parsed.max() - parsed.min()).total_seconds() / 3600

        txns_per_hour = len(parsed) / time_range_hours if time_range_hours > 0 else 0

        if txns_per_hour > 20:
            return 30, f"Very high transaction velocity: ~{txns_per_hour:.1f} transactions/hour"
        elif txns_per_hour > 10:
            return 20, f"High transaction velocity: ~{txns_per_hour:.1f} transactions/hour"
        elif txns_per_hour > 5:
            return 10, None
        else:
            return 0, None
    except Exception:
        return 0, None


def _score_to_level(score: int) -> str:
    """Converts a numeric score to a named risk level."""
    if score >= 75:
        return "Critical"
    elif score >= 50:
        return "High"
    elif score >= 25:
        return "Medium"
    else:
        return "Low"


# ── Quick test ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Import the data functions from blockchain_data.py
    from blockchain_data import get_wallet_info, get_wallet_transactions

    # Use the same verified test address from blockchain_data.py
    test_address = "rUeGuHYuWeaPgvNPWCudG2t6PXHd6PZQL5"

    print(f"\nRunning risk analysis on: {test_address}")
    print("=" * 60)

    account_info = get_wallet_info(test_address)
    transactions = get_wallet_transactions(test_address, limit=50)

    result = analyse_wallet(account_info, transactions)

    print(f"\n  Risk Score:  {result['score']} / 100")
    print(f"  Risk Level:  {result['level']}")
    print(f"\n  Red Flags Detected:")
    for flag in result["flags"]:
        print(f"    • {flag}")

    print(f"\n  Statistics:")
    stats = result["stats"]
    print(f"    Transactions analysed:   {stats.get('total_transactions_analysed', 0)}")
    print(f"    Unique counterparties:   {stats.get('unique_counterparties', 0)}")
    print(f"    Payment ratio:           {stats.get('payment_ratio', 0):.1%}")
    print(f"    Lifetime transactions:   {stats.get('lifetime_transactions', 0):,}")
    print(f"    Current XRP balance:     {stats.get('balance_xrp', 0):.2f} XRP")
    print(f"\n  Transaction type breakdown:")
    for tx_type, count in stats.get("transaction_types", {}).items():
        print(f"    {tx_type:<25} {count}")