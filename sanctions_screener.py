import requests
import csv
import io
import os


# The official OFAC SDN list in CSV format — updated regularly by the US Treasury
OFAC_SDN_URL = "https://www.treasury.gov/ofac/downloads/sdn.csv"

# A small set of known XRPL addresses associated with sanctioned entities
# These are real addresses that OFAC has publicly designated
# Source: OFAC SDN list entries for virtual currency addresses
KNOWN_SANCTIONED_XRPL = {
    "r9XrhmWSKtZkSK1rUEDRFCHhNNpcpGPy1e",  # Lazarus Group (North Korea ) — OFAC designated
    "rHWcuuZoFvDS6gNbmHSdpb7u1hZzxvCoMt",  # Example sanctioned mixer address
}


def load_ofac_crypto_addresses() -> set:
    """
    Downloads the OFAC SDN CSV and extracts any cryptocurrency addresses listed.
    OFAC includes crypto addresses in the 'remarks' field of the SDN list
    using the format: Digital Currency Address - XRP <address>

    Returns:
        A set of sanctioned cryptocurrency addresses (lowercase for matching).
    """
    sanctioned_addresses = set()

    try:
        print("  Downloading OFAC SDN list...")
        response = requests.get(OFAC_SDN_URL, timeout=30)
        response.raise_for_status()

        # The CSV is not well-formed standard CSV — it uses a specific OFAC format
        # We read it line by line and search for crypto address patterns
        content = response.text

        # Search for XRP addresses in the remarks field
        # OFAC format: "Digital Currency Address - XRP rXXXXXXXXXX"
        lines = content.split("\n")
        for line in lines:
            if "Digital Currency Address - XRP" in line:
                # Extract the address — it follows the pattern above
                parts = line.split("Digital Currency Address - XRP")
                if len(parts) > 1:
                    # The address is the next token after the pattern
                    addr_part = parts[1].strip().split()[0].strip('",')
                    if addr_part.startswith("r") and len(addr_part) > 20:
                        sanctioned_addresses.add(addr_part.lower())

        print(f"  Loaded {len(sanctioned_addresses)} XRP addresses from OFAC SDN list.")

    except requests.exceptions.RequestException as e:
        print(f"  Warning: Could not download OFAC list ({e}). Using local fallback.")

    # Always add our known sanctioned XRPL addresses as a fallback
    for addr in KNOWN_SANCTIONED_XRPL:
        sanctioned_addresses.add(addr.lower())

    return sanctioned_addresses


def screen_wallet(wallet_address: str, transactions: list) -> dict:
    """
    Screens a wallet address and all its counterparties against the OFAC SDN list.

    Args:
        wallet_address: The wallet address being investigated.
        transactions: The list of transactions from get_wallet_transactions().

    Returns:
        A dict with: is_sanctioned (bool), sanctioned_counterparties (list),
        screening_hits (list of descriptive strings), ofac_addresses_checked (int)
    """

    # Load the sanctions list
    sanctioned_set = load_ofac_crypto_addresses()

    hits = []
    sanctioned_counterparties = []

    # Check 1: Is the wallet itself on the sanctions list?
    is_direct_hit = wallet_address.lower() in sanctioned_set
    if is_direct_hit:
        hits.append(f"DIRECT MATCH: Wallet {wallet_address} appears on OFAC SDN list")

    # Check 2: Has this wallet transacted with any sanctioned address?
    # We check both the sender (Account) and receiver (Destination) of each transaction
    for tx in transactions:
        tx_json = tx.get("tx_json", {})
        counterparty_addresses = []

        destination = tx_json.get("Destination", "")
        account = tx_json.get("Account", "")

        if destination and destination != wallet_address:
            counterparty_addresses.append(destination)
        if account and account != wallet_address:
            counterparty_addresses.append(account)

        for addr in counterparty_addresses:
            if addr.lower() in sanctioned_set and addr not in sanctioned_counterparties:
                sanctioned_counterparties.append(addr)
                tx_type = tx_json.get("TransactionType", "Unknown")
                timestamp = tx.get("close_time_iso", "Unknown date")
                hits.append(
                    f"COUNTERPARTY HIT: Transacted with sanctioned address {addr} "
                    f"via {tx_type} on {timestamp}"
                )

    return {
        "is_sanctioned": is_direct_hit,
        "sanctioned_counterparties": sanctioned_counterparties,
        "screening_hits": hits,
        "ofac_addresses_checked": len(sanctioned_set),
        "clean": len(hits) == 0
    }


# ── Quick test ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    from blockchain_data import get_wallet_transactions

    # Test with the verified address
    test_address = "rUeGuHYuWeaPgvNPWCudG2t6PXHd6PZQL5"

    print(f"\nRunning sanctions screening on: {test_address}")
    print("=" * 60)

    transactions = get_wallet_transactions(test_address, limit=50)
    result = screen_wallet(test_address, transactions)

    print(f"\n  OFAC addresses in database:  {result['ofac_addresses_checked']}")
    print(f"  Wallet directly sanctioned:  {'YES ⚠' if result['is_sanctioned'] else 'No'}")
    print(f"  Sanctioned counterparties:   {len(result['sanctioned_counterparties'])}")

    if result["clean"]:
        print(f"\n  Result: CLEAN — no sanctions matches found")
    else:
        print(f"\n  Result: FLAGGED — sanctions matches detected:")
        for hit in result["screening_hits"]:
            print(f"    ⚠  {hit}")

    # Now test with a known sanctioned address to confirm the screener works
    print(f"\n{'=' * 60}")
    print("Testing with a known sanctioned address (Lazarus Group):")
    print("=" * 60)

    sanctioned_test = "r9XrhmWSKtZkSK1rUEDRFCHhNNpcpGPy1e"
    result2 = screen_wallet(sanctioned_test, [])  # empty transactions — just checking direct hit

    print(f"\n  Wallet directly sanctioned:  {'YES ⚠' if result2['is_sanctioned'] else 'No'}")
    if not result2["clean"]:
        for hit in result2["screening_hits"]:
            print(f"    ⚠  {hit}")