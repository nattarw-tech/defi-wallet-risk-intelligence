import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()


def generate_risk_narrative(
    wallet_address: str,
    risk_result: dict,
    sanctions_result: dict
) -> str:
    """
    Generates a plain-English AML risk narrative using an LLM.

    Takes the structured outputs from the risk engine and
    sanctions screener and produces a professional compliance
    summary suitable for a case file or SAR pre-filing note.

    Args:
        wallet_address: The wallet address that was analysed.
        risk_result: The dict returned by analyse_wallet() in risk_engine.py
        sanctions_result: The dict returned by screen_wallet() in sanctions_screener.py

    Returns:
        A string containing the AI-generated risk narrative.
    """

    # Retrieve the API key — checks .env file first, then GitHub Secrets
    api_key = os.getenv("DEFI_GROQ_API_KEY")

    if not api_key:
        return "Error: DEFI_GROQ_API_KEY not found. Check your .env file or GitHub Secrets."

    client = Groq(api_key=api_key)

    # Build a structured summary of the findings to pass to the model
    score = risk_result.get("score", 0)
    level = risk_result.get("level", "Unknown")
    flags = risk_result.get("flags", [])
    stats = risk_result.get("stats", {})
    is_sanctioned = sanctions_result.get("is_sanctioned", False)
    sanctioned_counterparties = sanctions_result.get("sanctioned_counterparties", [])
    sanctions_hits = sanctions_result.get("screening_hits", [])

    flags_text = "\n".join(f"- {f}" for f in flags)
    sanctions_text = "\n".join(f"- {h}" for h in sanctions_hits) if sanctions_hits else "- None"

    prompt = f"""You are a senior AML compliance analyst at a regulated financial institution.
You have just completed an automated risk assessment of the following XRP Ledger wallet address.
Write a concise, professional risk narrative suitable for inclusion in a compliance case file.

WALLET ADDRESS: {wallet_address}

RISK ASSESSMENT RESULTS:
- Risk Score: {score} / 100
- Risk Level: {level}
- Transactions Analysed: {stats.get('total_transactions_analysed', 'N/A')}
- Lifetime Transactions: {stats.get('lifetime_transactions', 'N/A'):,}
- Current XRP Balance: {stats.get('balance_xrp', 'N/A')} XRP
- Unique Counterparties: {stats.get('unique_counterparties', 'N/A')}
- Payment Ratio: {stats.get('payment_ratio', 0):.1%}

BEHAVIOURAL RED FLAGS DETECTED:
{flags_text}

SANCTIONS SCREENING RESULTS:
- Directly Sanctioned: {'YES' if is_sanctioned else 'No'}
- Sanctioned Counterparties Found: {len(sanctioned_counterparties)}
- Screening Hits:
{sanctions_text}

Write a narrative of 3 to 4 paragraphs covering:
1. A summary of the wallet's risk profile and overall assessment
2. The specific behavioural indicators that contributed to the risk score
3. The sanctions screening outcome
4. A recommended next step for the compliance team (e.g. enhanced due diligence, escalation, no action required)

Write in a formal, professional tone. Do not use bullet points in the narrative — write in full paragraphs.
Do not add any disclaimers or caveats about being an AI."""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,   # Low temperature = more consistent, factual output
            max_tokens=600
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        return f"Error generating narrative: {e}"


# ── Quick test ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    from blockchain_data import get_wallet_info, get_wallet_transactions
    from risk_engine import analyse_wallet
    from sanctions_screener import screen_wallet

    test_address = "rUeGuHYuWeaPgvNPWCudG2t6PXHd6PZQL5"

    print(f"\nGenerating AI risk narrative for: {test_address}")
    print("=" * 60)
    print("Fetching data...")

    account_info = get_wallet_info(test_address)
    transactions = get_wallet_transactions(test_address, limit=50)
    risk_result = analyse_wallet(account_info, transactions)
    sanctions_result = screen_wallet(test_address, transactions)

    print(f"Risk Score: {risk_result['score']} / 100 ({risk_result['level']})")
    print("Generating narrative...\n")

    narrative = generate_risk_narrative(test_address, risk_result, sanctions_result)

    print("─" * 60)
    print(narrative)
    print("─" * 60)