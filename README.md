# DeFi Wallet Risk Intelligence

Real-time AML screening and behavioural risk analysis for XRP Ledger wallets, powered by live on-chain data and AI-generated compliance narratives.

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://defi-wallet-risk-intelligence-jye2qznapkns8qkff3orrb.streamlit.app/)

---

## Overview

Financial crime on public blockchains is a growing challenge for compliance teams at banks, exchanges, and fintech firms. While blockchain transactions are fully transparent, the volume and complexity of on-chain activity makes manual review impractical at scale.

This project demonstrates a simplified AML screening pipeline for the XRP Ledger, the same type of tooling used commercially by firms such as Chainalysis, Elliptic, and TRM Labs. It fetches live wallet data, applies rule-based behavioural risk scoring, screens against the OFAC SDN sanctions list, and generates a plain-English compliance narrative using a large language model.

---

## Features

- **Live on-chain data:** fetches real transaction history directly from the XRP Ledger public API (no API key required)
- **Behavioural risk scoring:** four rule-based signals: transaction velocity, counterparty diversity, payment concentration, and volume-to-balance ratio
- **OFAC sanctions screening:** downloads the live US Treasury SDN list at runtime and screens the wallet and all its counterparties
- **AI compliance narrative:** generates a structured, professional risk summary using LLaMA 3.3 (70B) via Groq
- **Interactive dashboard:** Streamlit UI with risk metrics, sanctions result, behavioural flags, and transaction type chart

---

## Architecture

The project is structured as a modular pipeline. Each file has a single responsibility:

```
blockchain_data.py     →  Fetches wallet info and transactions from XRPL
risk_engine.py         →  Scores wallet behaviour across 4 risk signals
sanctions_screener.py  →  Screens wallet against OFAC SDN list
ai_narrator.py         →  Generates AI compliance narrative via Groq
app.py                 →  Streamlit dashboard — orchestrates all modules
```

Data flows in one direction: `blockchain_data` → `risk_engine` + `sanctions_screener` → `ai_narrator` → `app`.

---

## Risk Scoring Methodology

| Signal | Threshold | Points |
|---|---|---|
| Transaction velocity | > 50 tx/hour | +20 |
| Counterparty diversity | > 30 unique addresses in 50 tx | +15 |
| Payment concentration | > 85% of transactions are Payments | +15 |
| Extreme volume / low balance | > 50M lifetime tx, < 20 XRP held | +25 |

**Risk levels:** Low (0–24) · Medium (25–49) · High (50–74) · Critical (75–100)

---

## Tech Stack

| Component | Technology |
|---|---|
| Language | Python 3.12 |
| Dashboard | Streamlit |
| Data source | XRP Ledger public API (xrplcluster.com) |
| Sanctions data | OFAC SDN list (US Treasury, fetched live) |
| AI model | LLaMA 3.3 70B via Groq API |
| Charts | Plotly Express |
| Environment | GitHub Codespaces |

---

## Running Locally

### Prerequisites
- Python 3.11+
- A free [Groq API key](https://console.groq.com)

### Setup

```bash
git clone https://github.com/YOUR_USERNAME/defi-wallet-risk-intelligence.git
cd defi-wallet-risk-intelligence
pip install -r requirements.txt
```

Create a `.env` file in the project root:

```
DEFI_GROQ_API_KEY=your_groq_api_key_here
```

Run the app:

```bash
streamlit run app.py
```

---

## Sample Addresses to Try

| Address | Expected Result |
|---|---|
| `rf1BiGeXwwQoi8Z2ueFYTEXSwuJYfV2Jpn` | Medium risk — counterparty diversity flag |
| `rUeGuHYuWeaPgvNPWCudG2t6PXHd6PZQL5` | High risk — velocity + extreme volume flags |
| `r9XrhmWSKtZkSK1rUEDRFCHhNNpcpGPy1e` | Sanctions alert — OFAC SDN direct match |

---

## Limitations and Disclaimer

This project is a **portfolio demonstration** and is not intended for production compliance use. Key limitations:

- Analysis is based on the last 50 transactions only, not full wallet history
- The OFAC SDN list contains no XRP addresses at present; the sanctions demo uses a locally maintained address set
- Risk scoring uses simplified heuristics; a production tool would incorporate graph analysis, clustering, and entity resolution

---

## Future Enhancements

- Multi-chain support (Ethereum via Etherscan, Bitcoin via Blockstream)
- WebSocket live feed of top active wallets
- Graph visualisation of counterparty relationships
- Integration with a live threat intelligence feed (e.g. Elliptic API)
- Case management workflow with SAR export

---

## About

Built by **Nisrin Shoukat Attarwala**  
MSc Financial Technology & Innovation, Bayes Business School, 2026  

This project is part of a portfolio targeting roles in Fintech, RegTech, and Product Operations.  
See also: [RegTech Compliance Dashboard](https://github.com/nattarw-tech/regtech-compliance-dashboard)

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect_With_Me-blue?logo=linkedin&logoColor=white)](https://www.linkedin.com/in/nisrin-attarwala/)