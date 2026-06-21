import requests
import os
from dotenv import load_dotenv

# Load variables from the .env file into the environment
# This is needed for the Groq key
load_dotenv(  )


# The public XRPL node endpoint — no API key required
XRPL_ENDPOINT = "https://xrplcluster.com"


def get_wallet_transactions(wallet_address: str, limit: int = 50  ) -> list:
    """
    Fetches recent transactions for a given XRP Ledger wallet address.

    The XRPL JSON-RPC API uses POST requests with a JSON body.
    I use the 'account_tx' method, which returns a list of validated transactions involving the given account.

    Args:
        wallet_address: A valid XRPL wallet address (starts with 'r').
        limit: How many transactions to fetch. Default is 50.

    Returns:
        A list of transaction dictionaries, or an empty list on failure.
    """

    # This is the JSON payload I send to the XRPL node
    # method = what I want, 
    # params = the details of our request
    payload = {
        "method": "account_tx",
        "params": [
            {
                "account": wallet_address,
                "ledger_index_min": -1,   # -1 means "from the earliest available"
                "ledger_index_max": -1,   # -1 means "up to the most recent"
                "limit": limit,
                "forward": False          # False = most recent transactions first
            }
        ]
    }

    try:
        response = requests.post(XRPL_ENDPOINT, json=payload, timeout=15)
        response.raise_for_status()
        data = response.json()

        # The XRPL wraps its response in a "result" object
        result = data.get("result", {})

        # Check for errors returned by the XRPL node itself
        if result.get("status") == "error":
            print(f"XRPL Error: {result.get('error_message', 'Unknown error')}")
            return []

        # The actual list of transactions is inside result > transactions
        transactions = result.get("transactions", [])
        return transactions

    except requests.exceptions.Timeout:
        print("Error: The request to the XRPL node timed out.")
        return []
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to XRPL node: {e}")
        return []


def get_wallet_info(wallet_address: str) -> dict:
    """
    Fetches basic account information for a given XRPL wallet address.
    This gives us the XRP balance and the account's transaction sequence number,
    which tells us how old and how active the account is.

    Args:
        wallet_address: A valid XRPL wallet address (starts with 'r').

    Returns:
        A dictionary of account info, or an empty dict on failure.
    """

    payload = {
        "method": "account_info",
        "params": [
            {
                "account": wallet_address,
                "ledger_index": "validated"  # Use the latest validated ledger
            }
        ]
    }

    try:
        response = requests.post(XRPL_ENDPOINT, json=payload, timeout=15)
        response.raise_for_status()
        data = response.json()

        result = data.get("result", {})

        if result.get("status") == "error":
            print(f"XRPL Error: {result.get('error_message', 'Unknown error')}")
            return {}

        # The account details are inside result > account_data
        return result.get("account_data", {})

    except requests.exceptions.RequestException as e:
        print(f"Error fetching account info: {e}")
        return {}


# ── Quick test ──────────────────────────────────────────────────────────────
# This block only runs when you execute this file directly:
#   python blockchain_data.py
# It does NOT run when other files import this module.

if __name__ == "__main__":

    # A well-known, high-activity public XRPL address (Bitstamp exchange wallet)
    # This is a public exchange address — safe to use for testing
    test_address = "rDf5rV5izb5wTEFmFnJ5j48Vcjt7SrkFkv"

    print(f"\nFetching account info for: {test_address}")
    print("-" * 60)

    account_info = get_wallet_info(test_address)

    if account_info:
        # XRP balances on the ledger are stored in 'drops' (1 XRP = 1,000,000 drops)
        balance_xrp = int(account_info.get("Balance", 0)) / 1_000_000
        sequence = account_info.get("Sequence", 0)
        print(f"  XRP Balance:        {balance_xrp:,.2f} XRP")
        print(f"  Transaction Count:  {sequence:,} (lifetime transactions)")
    else:
        print("  Could not retrieve account info.")

    print(f"\nFetching last 10 transactions for: {test_address}")
    print("-" * 60)

    transactions = get_wallet_transactions(test_address, limit=10)

    if transactions:
        print(f"  SUCCESS — fetched {len(transactions)} transactions.\n")
        print("  Most recent transaction:")
        tx = transactions[0]

        # The transaction details are nested inside tx > tx_json
        tx_json = tx.get("tx_json", {})
        tx_type = tx_json.get("TransactionType", "Unknown")

        # hash and close_time_iso can appear at the top level OR inside tx_json
        # depending on the API version — checking both places
        tx_hash = tx.get("hash") or tx_json.get("hash", "N/A")
        close_time = tx.get("close_time_iso") or tx_json.get("close_time_iso", "N/A")


        print(f"    Type:      {tx_type}")
        print(f"    Hash:      {tx_hash}")
        print(f"    Timestamp: {close_time}")

        # If it is a Payment transaction, show the amount
        if tx_type == "Payment":
            amount = tx_json.get("Amount", {})
            if isinstance(amount, str):
                # A plain string means it is an XRP payment (in drops)
                xrp_amount = int(amount) / 1_000_000
                print(f"    Amount:    {xrp_amount:.6f} XRP")
            elif isinstance(amount, dict):
                # A dict means it is a token (IOU) payment
                print(f"    Amount:    {amount.get('value')} {amount.get('currency')}")
    else:
        print("  FAILED — no transactions returned.")
        print("  Check that the wallet address is valid and the XRPL node is reachable.")