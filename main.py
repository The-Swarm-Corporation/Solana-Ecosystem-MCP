from datetime import datetime
import os
from typing import Any, Dict, List, Optional, Union

import requests
import httpx
from fastmcp import FastMCP
from pydantic import BaseModel, Field
from enum import Enum
from dotenv import load_dotenv

load_dotenv()


# Common models
class TokenMetadata(BaseModel):
    """Metadata for a Solana token"""
    symbol: str = Field(..., description="Token symbol")
    name: str = Field(..., description="Token name")
    decimals: int = Field(..., description="Token decimals")
    logo: Optional[str] = Field(None, description="URL to token logo")
    coingecko_id: Optional[str] = Field(None, description="CoinGecko ID for the token")


class Price(BaseModel):
    """Price information for a token"""
    usd: float = Field(..., description="Price in USD")
    usd_24h_change: Optional[float] = Field(None, description="24h price change percentage")
    sol: Optional[float] = Field(None, description="Price in SOL")


# SolScan Models
class SolscanAccountType(str, Enum):
    TOKEN = "token"
    ACCOUNT = "account"
    NFT = "nft"
    PROGRAM = "program"


class SolscanAccountInfo(BaseModel):
    """Information about a Solana account from Solscan"""
    address: str = Field(..., description="Solana account address")
    type: SolscanAccountType = Field(..., description="Type of the account")
    owner: Optional[str] = Field(None, description="Owner of the account")
    executable: bool = Field(..., description="Whether the account is executable")
    lamports: int = Field(..., description="Amount of lamports in the account")
    rent_epoch: int = Field(..., description="Rent epoch")
    data: Optional[Any] = Field(None, description="Account data")


class SolscanTransactionInfo(BaseModel):
    """Information about a Solana transaction from Solscan"""
    signature: str = Field(..., description="Transaction signature")
    block: int = Field(..., description="Block number")
    slot: int = Field(..., description="Slot number")
    fee: int = Field(..., description="Transaction fee in lamports")
    status: str = Field(..., description="Transaction status")
    timestamp: int = Field(..., description="Transaction timestamp")
    signer: List[str] = Field(..., description="Transaction signers")
    log_messages: Optional[List[str]] = Field(None, description="Transaction log messages")


class SolscanTokenHolderInfo(BaseModel):
    """Information about a token holder from Solscan"""
    address: str = Field(..., description="Address of the holder")
    owner: Optional[str] = Field(None, description="Owner of the token account")
    amount: float = Field(..., description="Amount of tokens held")
    percent: float = Field(..., description="Percentage of total supply held")
    rank: int = Field(..., description="Rank of the holder by amount held")


class SolscanTokenInfo(BaseModel):
    """Information about a Solana token from Solscan"""
    address: str = Field(..., description="Token mint address")
    symbol: str = Field(..., description="Token symbol")
    name: str = Field(..., description="Token name")
    icon: Optional[str] = Field(None, description="URL to token icon")
    decimals: int = Field(..., description="Token decimals")
    supply: float = Field(..., description="Total token supply")
    holder_count: Optional[int] = Field(None, description="Number of token holders")
    price: Optional[Price] = Field(None, description="Token price information")


# Jupiter Models
class JupiterToken(BaseModel):
    """Token information for Jupiter API"""
    address: str = Field(..., description="Token mint address")
    chainId: int = Field(..., description="Chain ID")
    decimals: int = Field(..., description="Token decimals")
    name: str = Field(..., description="Token name")
    symbol: str = Field(..., description="Token symbol")
    logoURI: Optional[str] = Field(None, description="URL to token logo")
    tags: Optional[List[str]] = Field(None, description="Token tags")
    verified: Optional[bool] = Field(None, description="Whether the token is verified")


class JupiterQuoteRequest(BaseModel):
    """Request parameters for Jupiter quote API"""
    inputMint: str = Field(..., description="Input token mint address")
    outputMint: str = Field(..., description="Output token mint address")
    amount: str = Field(..., description="Amount in input token's smallest unit (lamports)")
    slippageBps: int = Field(50, description="Allowed slippage in basis points (1 bps = 0.01%)")
    platformFeeBps: Optional[int] = Field(None, description="Platform fee in basis points")
    onlyDirectRoutes: Optional[bool] = Field(False, description="Only use direct routes")
    asLegacyTransaction: Optional[bool] = Field(False, description="Return as legacy transaction")


class JupiterRoute(BaseModel):
    """Route information from Jupiter API"""
    inAmount: str = Field(..., description="Input amount")
    outAmount: str = Field(..., description="Output amount")
    amount: str = Field(..., description="Amount")
    otherAmountThreshold: str = Field(..., description="Minimum amount out")
    swapMode: str = Field(..., description="Swap mode")
    slippageBps: int = Field(..., description="Slippage in basis points")
    priceImpactPct: str = Field(..., description="Price impact percentage")
    marketInfos: List[Dict[str, Any]] = Field(..., description="Market information")


class JupiterQuoteResponse(BaseModel):
    """Response from Jupiter quote API"""
    inputMint: str = Field(..., description="Input token mint address")
    outputMint: str = Field(..., description="Output token mint address")
    inAmount: str = Field(..., description="Input amount")
    outAmount: str = Field(..., description="Output amount")
    otherAmountThreshold: str = Field(..., description="Minimum amount out")
    swapMode: str = Field(..., description="Swap mode")
    slippageBps: int = Field(..., description="Slippage in basis points")
    priceImpactPct: str = Field(..., description="Price impact percentage")
    routes: List[JupiterRoute] = Field(..., description="Available routes")


# DexScreener Models
class DexScreenerPair(BaseModel):
    """Pair information from DexScreener"""
    chainId: str = Field(..., description="Chain ID")
    dexId: str = Field(..., description="DEX ID")
    url: str = Field(..., description="URL to pair page")
    pairAddress: str = Field(..., description="Pair address")
    baseToken: TokenMetadata = Field(..., description="Base token information")
    quoteToken: TokenMetadata = Field(..., description="Quote token information")
    priceNative: str = Field(..., description="Price in native token")
    priceUsd: Optional[str] = Field(None, description="Price in USD")
    txns: Dict[str, Any] = Field(..., description="Transaction statistics")
    volume: Dict[str, Any] = Field(..., description="Volume statistics")
    liquidity: Dict[str, Any] = Field(..., description="Liquidity information")


class DexScreenerSearchResponse(BaseModel):
    """Response from DexScreener search API"""
    pairs: List[DexScreenerPair] = Field(..., description="List of pairs")


# Create MCP server
mcp = FastMCP("solana-api")


# Solscan Tools
@mcp.tool(name="solscan_account_info", description="Get account information from Solscan")
async def solscan_account_info(address: str) -> Dict[str, Any]:
    """
    Get detailed information about a Solana account from Solscan.
    
    Args:
        address: The address of the Solana account
        
    Returns:
        Account information
    """
    api_key = os.getenv("SOLSCAN_API_KEY", "")
    headers = {"accept": "application/json"}
    if api_key:
        headers["token"] = api_key
        
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://public-api.solscan.io/account/{address}",
            headers=headers
        )
        response.raise_for_status()
        return response.json()


@mcp.tool(name="solscan_token_info", description="Get token information from Solscan")
async def solscan_token_info(address: str) -> Dict[str, Any]:
    """
    Get detailed information about a Solana token from Solscan.
    
    Args:
        address: The mint address of the token
        
    Returns:
        Token information
    """
    api_key = os.getenv("SOLSCAN_API_KEY", "")
    headers = {"accept": "application/json"}
    if api_key:
        headers["token"] = api_key
        
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://public-api.solscan.io/token/meta?tokenAddress={address}",
            headers=headers
        )
        response.raise_for_status()
        return response.json()


@mcp.tool(name="solscan_token_holders", description="Get token holders from Solscan")
async def solscan_token_holders(
    address: str, 
    limit: int = 10, 
    offset: int = 0
) -> Dict[str, Any]:
    """
    Get holders of a Solana token from Solscan.
    
    Args:
        address: The mint address of the token
        limit: Maximum number of holders to return
        offset: Pagination offset
        
    Returns:
        List of token holders
    """
    api_key = os.getenv("SOLSCAN_API_KEY", "")
    headers = {"accept": "application/json"}
    if api_key:
        headers["token"] = api_key
        
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://public-api.solscan.io/token/holders?tokenAddress={address}&limit={limit}&offset={offset}",
            headers=headers
        )
        response.raise_for_status()
        return response.json()


@mcp.tool(name="solscan_transaction", description="Get transaction details from Solscan")
async def solscan_transaction(signature: str) -> Dict[str, Any]:
    """
    Get detailed information about a Solana transaction from Solscan.
    
    Args:
        signature: The transaction signature
        
    Returns:
        Transaction details
    """
    api_key = os.getenv("SOLSCAN_API_KEY", "")
    headers = {"accept": "application/json"}
    if api_key:
        headers["token"] = api_key
        
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://public-api.solscan.io/transaction/{signature}",
            headers=headers
        )
        response.raise_for_status()
        return response.json()


# Jupiter Tools
@mcp.tool(name="jupiter_tokens", description="Get list of tokens from Jupiter")
async def jupiter_tokens() -> Dict[str, Any]:
    """
    Get the list of tokens supported by Jupiter.
    
    Returns:
        List of tokens
    """
    async with httpx.AsyncClient() as client:
        response = await client.get("https://token.jup.ag/all")
        response.raise_for_status()
        return response.json()


@mcp.tool(name="jupiter_price", description="Get token price from Jupiter")
async def jupiter_price(
    ids: List[str],
    vsToken: str = "USDC"
) -> Dict[str, Any]:
    """
    Get prices of tokens from Jupiter.
    
    Args:
        ids: List of token mint addresses
        vsToken: Token to get prices against (default: USDC)
        
    Returns:
        Token prices
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://price.jup.ag/v4/price?ids={','.join(ids)}&vsToken={vsToken}"
        )
        response.raise_for_status()
        return response.json()


@mcp.tool(name="jupiter_quote", description="Get swap quote from Jupiter")
async def jupiter_quote(quote_request: JupiterQuoteRequest) -> Dict[str, Any]:
    """
    Get a swap quote from Jupiter.
    
    Args:
        quote_request: Quote request parameters
        
    Returns:
        Swap quote information
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://quote-api.jup.ag/v6/quote",
            params=quote_request.model_dump()
        )
        response.raise_for_status()
        return response.json()


# DEX Screener Tools
@mcp.tool(name="dexscreener_token", description="Get token information from DEX Screener")
async def dexscreener_token(tokenAddress: str) -> Dict[str, Any]:
    """
    Get information about a token from DEX Screener.
    
    Args:
        tokenAddress: The token address
        
    Returns:
        Token information
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://api.dexscreener.com/latest/dex/tokens/{tokenAddress}"
        )
        response.raise_for_status()
        return response.json()


@mcp.tool(name="dexscreener_pair", description="Get pair information from DEX Screener")
async def dexscreener_pair(pairAddress: str) -> Dict[str, Any]:
    """
    Get information about a trading pair from DEX Screener.
    
    Args:
        pairAddress: The pair address
        
    Returns:
        Pair information
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://api.dexscreener.com/latest/dex/pairs/solana/{pairAddress}"
        )
        response.raise_for_status()
        return response.json()


@mcp.tool(name="dexscreener_search", description="Search on DEX Screener")
async def dexscreener_search(query: str) -> Dict[str, Any]:
    """
    Search for tokens or pairs on DEX Screener.
    
    Args:
        query: Search query (token name, symbol, or address)
        
    Returns:
        Search results
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://api.dexscreener.com/latest/dex/search?q={query}"
        )
        response.raise_for_status()
        return response.json()


if __name__ == "__main__":
    mcp.run(transport="sse")
