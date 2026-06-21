import streamlit as st
import pandas as pd
import plotly.express as px
from blockchain_data import get_wallet_info, get_wallet_transactions
from risk_engine import analyse_wallet
from sanctions_screener import screen_wallet
from ai_narrator import generate_risk_narrative


# ── Page configuration ────────────────────────────────────────────────────────
st.set_page_config(
    page_title="DeFi Wallet Risk Intelligence",
    page_icon="🔍",
    layout="wide"
)

# ── Header ────────────────────────────────────────────────────────────────────
st.title("🔍 DeFi Wallet Risk Intelligence")
st.markdown(
    "Real-time AML screening and behavioural risk analysis for XRP Ledger wallets. "
    "Enter any XRPL wallet address to generate a compliance risk assessment."
)
st.divider()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("About This Tool")
    st.markdown("""
    This tool analyses XRP Ledger wallets for AML risk indicators using:

    - **Live on-chain data** from the XRP Ledger public API
    - **Behavioural scoring** across 4 risk signals
    - **OFAC SDN screening** against the live US Treasury sanctions list
    - **AI narrative generation** using LLaMA 3 via Groq

    **Risk Levels**
    - 🟢 Low (0–24)
    - 🟡 Medium (25–49)
    - 🟠 High (50–74)
    - 🔴 Critical (75–100)
    """)

    st.divider()
    st.markdown("**Sample addresses to try:**")
    st.code("rf1BiGeXwwQoi8Z2ueFYTEXSwuJYfV2Jpn", language=None)
    st.code("rUeGuHYuWeaPgvNPWCudG2t6PXHd6PZQL5", language=None)
    st.code("r9XrhmWSKtZkSK1rUEDRFCHhNNpcpGPy1e", language=None)

    st.markdown("---")
    st.markdown(
        "<p style='font-size:0.75rem;color:#9ca3af;'>Built by Nisrin Shoukat Attarwala<br/>MSc Financial Technology &amp; Innovation<br/>Bayes Business School<br/>2026</p>",
        unsafe_allow_html=True
    )

# ── Input ─────────────────────────────────────────────────────────────────────
wallet_input = st.text_input(
    label="Enter XRPL Wallet Address",
    placeholder="e.g. rf1BiGeXwwQoi8Z2ueFYTEXSwuJYfV2Jpn",
    help="XRP Ledger addresses start with the letter 'r' and are 25–34 characters long."
)

analyse_button = st.button("🔍 Analyse Wallet", type="primary", use_container_width=True)

# ── Analysis ──────────────────────────────────────────────────────────────────
if analyse_button and wallet_input:

    # Basic format validation
    if not wallet_input.startswith("r") or len(wallet_input) < 25:
        st.error("That does not look like a valid XRPL address. Addresses start with 'r' and are at least 25 characters long.")
        st.stop()

    with st.spinner("Fetching live blockchain data..."):
        account_info = get_wallet_info(wallet_input)
        transactions = get_wallet_transactions(wallet_input, limit=50)

    if not account_info:
        st.error("Could not retrieve data for that address. Please check the address and try again.")
        st.stop()

    with st.spinner("Running risk analysis and sanctions screening..."):
        risk_result = analyse_wallet(account_info, transactions)
        sanctions_result = screen_wallet(wallet_input, transactions)

    # ── Risk Score Display ────────────────────────────────────────────────────
    score = risk_result["score"]
    level = risk_result["level"]

    # Colour coding for risk level
    level_colours = {
        "Low": "🟢",
        "Medium": "🟡",
        "High": "🟠",
        "Critical": "🔴",
        "Unknown": "⚪"
    }
    icon = level_colours.get(level, "⚪")

    st.subheader(f"Risk Assessment: {icon} {level} Risk")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Risk Score", f"{score} / 100")
    col2.metric("Lifetime Transactions", f"{risk_result['stats'].get('lifetime_transactions', 0):,}")
    col3.metric("XRP Balance", f"{risk_result['stats'].get('balance_xrp', 0):.2f} XRP")
    col4.metric("Unique Counterparties", risk_result['stats'].get('unique_counterparties', 0))

    # ── Sanctions Result ──────────────────────────────────────────────────────
    st.divider()
    st.subheader("Sanctions Screening")

    if not sanctions_result["clean"]:
        st.error(f"⚠️ SANCTIONS ALERT — {len(sanctions_result['screening_hits'])} hit(s) detected")
        for hit in sanctions_result["screening_hits"]:
            st.warning(hit)
    else:
        st.success(f"✅ CLEAN — No matches found across {sanctions_result['ofac_addresses_checked']} screened addresses")

    # ── Behavioural Flags ─────────────────────────────────────────────────────
    st.divider()
    st.subheader("Behavioural Risk Flags")

    flags = risk_result["flags"]
    if "No significant risk indicators detected" in flags:
        st.success("✅ No significant behavioural risk indicators detected")
    else:
        for flag in flags:
            st.warning(f"⚠️ {flag}")

    # ── Transaction Breakdown Chart ───────────────────────────────────────────
    st.divider()
    st.subheader("Transaction Type Breakdown")

    tx_types = risk_result["stats"].get("transaction_types", {})
    if tx_types:
        chart_df = pd.DataFrame(
            list(tx_types.items()),
            columns=["Transaction Type", "Count"]
        ).sort_values("Count", ascending=False)

        fig = px.bar(
            chart_df,
            x="Transaction Type",
            y="Count",
            color="Count",
            color_continuous_scale="Reds",
            title=f"Last {risk_result['stats'].get('total_transactions_analysed', 50)} Transactions by Type"
        )
        fig.update_layout(showlegend=False, coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)

    # ── AI Narrative ──────────────────────────────────────────────────────────
    st.divider()
    st.subheader("AI-Generated Compliance Narrative")

    with st.spinner("Generating compliance narrative..."):
        narrative = generate_risk_narrative(wallet_input, risk_result, sanctions_result)

    st.info(narrative)

    # ── Raw Stats Expander ────────────────────────────────────────────────────
    with st.expander("View Raw Statistics"):
        st.json(risk_result["stats"])

elif analyse_button and not wallet_input:
    st.warning("Please enter a wallet address before clicking Analyse.")