import os
import json
from typing import List, Dict, Any, Optional
from openai import OpenAI
from dotenv import load_dotenv
import requests
from datetime import datetime, timedelta

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# The Graph API configuration
GRAPH_API_KEY = os.getenv("GRAPH_API_KEY")

# The Graph endpoint for Uniswap V3 (Ethereum mainnet)
UNISWAP_V3_SUBGRAPH = f"https://gateway.thegraph.com/api/{GRAPH_API_KEY}/subgraphs/id/5zvR82QoaXYFyDEKLZ9t6v9adgnptxYpKpSbxtgVENFV"

# ============= DEX LIQUIDITY TOOLS =============

def get_tvl(pool_address: str) -> Dict[str, Any]:
    """
    Get Total Value Locked (TVL) in USD for a specific Uniswap V3 pool.

    Args:
        pool_address: The contract address of the pool (e.g., "0x...")

    Returns:
        Dict with TVL information
    """
    query = """
    query GetPoolTVL($poolAddress: String!) {
        pool(id: $poolAddress) {
            id
            token0 {
                symbol
                name
            }
            token1 {
                symbol
                name
            }
            totalValueLockedUSD
            totalValueLockedToken0
            totalValueLockedToken1
            feeTier
        }
    }
    """

    variables = {"poolAddress": pool_address.lower()}

    try:
        response = requests.post(
            UNISWAP_V3_SUBGRAPH,
            json={"query": query, "variables": variables}
        )
        response.raise_for_status()
        data = response.json()

        if "errors" in data:
            return {"error": f"GraphQL errors: {data['errors']}"}

        pool = data.get("data", {}).get("pool")
        if not pool:
            return {"error": f"Pool {pool_address} not found"}

        return {
            "pool_address": pool["id"],
            "pair": f"{pool['token0']['symbol']}/{pool['token1']['symbol']}",
            "tvl_usd": float(pool["totalValueLockedUSD"]),
            "tvl_token0": float(pool["totalValueLockedToken0"]),
            "tvl_token1": float(pool["totalValueLockedToken1"]),
            "fee_tier": int(pool["feeTier"]) / 10000,  # Convert to percentage
            "token0": pool["token0"]["symbol"],
            "token1": pool["token1"]["symbol"]
        }
    except Exception as e:
        return {"error": f"Failed to fetch TVL: {str(e)}"}


def get_volume(pool_address: str, period: str = "24h") -> Dict[str, Any]:
    """
    Get trading volume for a specific Uniswap V3 pool.

    Args:
        pool_address: The contract address of the pool
        period: Time period - "24h", "7d", or "30d"

    Returns:
        Dict with volume information
    """
    # Calculate timestamp based on period
    now = datetime.now()
    if period == "24h":
        start_timestamp = int((now - timedelta(days=1)).timestamp())
        days = 1
    elif period == "7d":
        start_timestamp = int((now - timedelta(days=7)).timestamp())
        days = 7
    elif period == "30d":
        start_timestamp = int((now - timedelta(days=30)).timestamp())
        days = 30
    else:
        return {"error": "Invalid period. Use '24h', '7d', or '30d'"}

    query = """
    query GetPoolVolume($poolAddress: String!, $startTime: Int!) {
        pool(id: $poolAddress) {
            id
            token0 {
                symbol
            }
            token1 {
                symbol
            }
        }
        poolDayDatas(
            where: {pool: $poolAddress, date_gte: $startTime}
            orderBy: date
            orderDirection: desc
        ) {
            date
            volumeUSD
            volumeToken0
            volumeToken1
            feesUSD
        }
    }
    """

    variables = {
        "poolAddress": pool_address.lower(),
        "startTime": start_timestamp
    }

    try:
        response = requests.post(
            UNISWAP_V3_SUBGRAPH,
            json={"query": query, "variables": variables}
        )
        response.raise_for_status()
        data = response.json()

        if "errors" in data:
            return {"error": f"GraphQL errors: {data['errors']}"}

        pool = data.get("data", {}).get("pool")
        pool_day_datas = data.get("data", {}).get("poolDayDatas", [])

        if not pool:
            return {"error": f"Pool {pool_address} not found"}

        # Sum up volume for the period
        total_volume_usd = sum(float(day["volumeUSD"]) for day in pool_day_datas)
        total_fees_usd = sum(float(day["feesUSD"]) for day in pool_day_datas)

        # Calculate daily average
        avg_daily_volume = total_volume_usd / days if days > 0 else 0
        avg_daily_fees = total_fees_usd / days if days > 0 else 0

        return {
            "pool_address": pool["id"],
            "pair": f"{pool['token0']['symbol']}/{pool['token1']['symbol']}",
            "period": period,
            "total_volume_usd": total_volume_usd,
            "average_daily_volume_usd": avg_daily_volume,
            "total_fees_usd": total_fees_usd,
            "average_daily_fees_usd": avg_daily_fees,
            "data_points": len(pool_day_datas)
        }
    except Exception as e:
        return {"error": f"Failed to fetch volume: {str(e)}"}


def get_apy(pool_address: str) -> Dict[str, Any]:
    """
    Calculate APY (Annual Percentage Yield) for a Uniswap V3 pool based on fees and TVL.

    Args:
        pool_address: The contract address of the pool

    Returns:
        Dict with APY information
    """
    # First get TVL
    tvl_data = get_tvl(pool_address)
    if "error" in tvl_data:
        return tvl_data

    tvl_usd = tvl_data["tvl_usd"]
    if tvl_usd <= 0:
        return {"error": "TVL is zero or negative, cannot calculate APY"}

    # Get 24h volume and fees
    volume_data = get_volume(pool_address, "24h")
    if "error" in volume_data:
        return volume_data

    daily_fees = volume_data["total_fees_usd"]

    # Calculate APY
    # Formula: APY = ((1 + daily_rate) ^ 365) - 1
    daily_rate = daily_fees / tvl_usd
    apy = ((1 + daily_rate) ** 365 - 1) * 100  # Convert to percentage

    # Also calculate 7-day and 30-day APY for comparison
    volume_7d = get_volume(pool_address, "7d")
    volume_30d = get_volume(pool_address, "30d")

    apy_7d = 0
    apy_30d = 0

    if "error" not in volume_7d:
        daily_fees_7d = volume_7d["average_daily_fees_usd"]
        daily_rate_7d = daily_fees_7d / tvl_usd
        apy_7d = ((1 + daily_rate_7d) ** 365 - 1) * 100

    if "error" not in volume_30d:
        daily_fees_30d = volume_30d["average_daily_fees_usd"]
        daily_rate_30d = daily_fees_30d / tvl_usd
        apy_30d = ((1 + daily_rate_30d) ** 365 - 1) * 100

    return {
        "pool_address": pool_address,
        "pair": tvl_data["pair"],
        "fee_tier": tvl_data["fee_tier"],
        "tvl_usd": tvl_usd,
        "apy_24h": round(apy, 2),
        "apy_7d": round(apy_7d, 2),
        "apy_30d": round(apy_30d, 2),
        "daily_fees_usd": daily_fees,
        "daily_rate": round(daily_rate * 100, 4),  # As percentage
        "note": "APY calculated from fees generated, actual returns may vary due to impermanent loss"
    }


# ============= REACT AGENT =============

class DexLiquidityAgent:
    def __init__(self, model: str = "gpt-4o-mini"):
        self.model = model
        self.max_iterations = 10
        # Available functions mapping
        self.available_functions = {
            "get_tvl": get_tvl,
            "get_volume": get_volume,
            "get_apy": get_apy
        }

        # Tools definition for OpenAI
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_tvl",
                    "description": "Get Total Value Locked (TVL) in USD for a specific Uniswap V3 pool",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "pool_address": {
                                "type": "string",
                                "description": "The contract address of the Uniswap V3 pool (e.g., '0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640' for USDC/WETH 0.05% pool)"
                            }
                        },
                        "required": ["pool_address"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_volume",
                    "description": "Get trading volume for a specific Uniswap V3 pool",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "pool_address": {
                                "type": "string",
                                "description": "The contract address of the Uniswap V3 pool"
                            },
                            "period": {
                                "type": "string",
                                "description": "Time period for volume data: '24h', '7d', or '30d'",
                                "enum": ["24h", "7d", "30d"]
                            }
                        },
                        "required": ["pool_address"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_apy",
                    "description": "Calculate APY (Annual Percentage Yield) for a Uniswap V3 pool based on fees and TVL",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "pool_address": {
                                "type": "string",
                                "description": "The contract address of the Uniswap V3 pool"
                            }
                        },
                        "required": ["pool_address"]
                    }
                }
            }
        ]

    def run(self, messages: List[Dict[str, Any]]) -> str:
        """
        Run the ReAct agent with the given messages.
        """
        iteration = 0

        while iteration < self.max_iterations:
            iteration += 1
            print(f"\n🔄 Iteration {iteration}")

            # Call OpenAI with current messages and tools
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=self.tools,
                parallel_tool_calls=False  # Sequential execution
            )

            response_message = response.choices[0].message
            messages.append(response_message.model_dump())

            # Check if there are tool calls
            if response_message.tool_calls:
                print(f"🛠️  Executing {len(response_message.tool_calls)} tool(s)")

                for tool_call in response_message.tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)

                    print(f"   - Calling {function_name} with args: {function_args}")

                    # Execute the function
                    function_to_call = self.available_functions[function_name]
                    function_response = function_to_call(**function_args)

                    # Add function response to messages
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(function_response)
                    })
            else:
                # No more tool calls, return final response
                print("✅ Agent completed task")
                return response_message.content

        return "❌ Maximum iterations reached. The agent couldn't complete the task."


# ============= MAIN EXECUTION =============

def main():
    # Initialize the agent
    agent = DexLiquidityAgent()

    # System prompt
    system_message = """You are a DeFi analyst AI assistant specializing in Uniswap V3 liquidity pools.
    You can provide detailed metrics about pools including TVL, trading volume, and APY calculations.

    When analyzing pools:
    1. Always provide context about what the metrics mean
    2. Explain any significant findings
    3. Mention potential risks when discussing APY (like impermanent loss)
    4. Format numbers nicely (use commas for thousands, round decimals appropriately)

    You can analyze ANY valid Uniswap V3 pool address. Some popular examples include:
    - USDC/WETH 0.05%: 0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640
    - WBTC/WETH 0.05%: 0xcbcdf9626bc03e24f779434178a73a0b4bad62ed
    - USDC/WETH 0.30%: 0x8ad599c3a0ff1de082011efddc58f1908eb6e6d8
    
    But you're NOT limited to these - you can analyze any valid pool address the user provides!
    """

    print("🤖 DEX Liquidity AI Agent Started!")
    print("=" * 50)
    print("Available commands:")
    print("- Ask about TVL, volume, or APY for any Uniswap V3 pool")
    print("- Example: 'What's the TVL and APY for the USDC/WETH 0.05% pool?'")
    print("- Type 'exit' to quit")
    print("=" * 50)

    while True:
        user_input = input("\n💬 You: ").strip()

        if user_input.lower() in ['exit', 'quit', 'bye']:
            print("👋 Goodbye!")
            break

        if not user_input:
            continue

        # Prepare messages
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_input}
        ]

        # Run the agent
        print("\n🤔 Thinking...")
        response = agent.run(messages)

        print(f"\n🤖 Agent: {response}")


if __name__ == "__main__":
    main()