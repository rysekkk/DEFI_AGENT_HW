# DEX Liquidity AI Agent 🤖
AI agent for analyzing Uniswap V3 liquidity pools, providing insights on TVL, trading volume, and APY calculations.
## ✨ Features
- **TVL (Total Value Locked)** - total value locked in pools
- **Volume** - trading volume for 24h/7d/30d periods
- **APY** - annual percentage yield based on fees
- **Interactive chat** - natural conversation with AI agent

## 🛠️ Prerequisites
### Python
- Python 3.12+ (managed with uv)
- uv package manager

### API Keys
You'll need:
1. **OpenAI API key** - for AI functionality
2. **The Graph API key** - for Uniswap V3 data

## 📦 Installation
### 1. Clone repository:
``` bash
git clone https://github.com/rysekkk/DEFI_AGENT_HW.git
cd DEFI_AGENT_HW
```
### 2. Install uv (if not already installed):
``` bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```
### 3. Install dependencies with uv:
``` bash
uv add openai python-dotenv requests
```
### 4. Setup environment variables:
Create a `.env` file in the root directory:
``` bash
OPENAI_API_KEY=your_openai_api_key_here
GRAPH_API_KEY=your_graph_api_key_here
```
#### How to get API keys:
**OpenAI API key:**
1. Go to [platform.openai.com](https://platform.openai.com/)
2. Sign up/login
3. API → API keys → Create new secret key

**The Graph API key:**
1. Go to [thegraph.com](https://thegraph.com/)
2. Sign up/login
3. Studio → API keys → Create API key

## 🚀 Running the Agent
``` bash
uv run python DEX_AGENT.py
```
## 💬 Usage Examples
``` 
💬 You: What's the TVL and APY for the USDC/WETH 0.05% pool?

💬 You: Show me volume data for pool 0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640

💬 You: Compare APY between different fee tiers for USDC/WETH pools

💬 You: What's the current TVL in the WBTC/WETH pool?
```
