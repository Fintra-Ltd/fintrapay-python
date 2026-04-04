"""Type hints and constants for FintraPay SDK."""

# Supported blockchains
CHAINS = ["tron", "bsc", "ethereum", "solana", "base", "arbitrum", "polygon"]

# Supported tokens
TOKENS = ["USDT", "USDC", "DAI", "FDUSD", "TUSD", "PYUSD"]

# Token availability per chain
TOKEN_CHAINS = {
    "USDT": ["tron", "bsc", "ethereum", "solana", "base", "arbitrum", "polygon"],
    "USDC": ["bsc", "ethereum", "solana", "base", "arbitrum", "polygon"],
    "DAI": ["bsc", "ethereum", "base", "arbitrum", "polygon"],
    "FDUSD": ["bsc", "ethereum"],
    "TUSD": ["tron", "bsc", "ethereum"],
    "PYUSD": ["ethereum", "solana"],
}

# Invoice statuses
INVOICE_PENDING = "pending"
INVOICE_AWAITING = "awaiting_selection"
INVOICE_PAID = "paid"
INVOICE_CONFIRMED = "confirmed"
INVOICE_EXPIRED = "expired"
INVOICE_PARTIALLY_PAID = "partially_paid"

# Payout reasons
PAYOUT_REASONS = ["payment", "refund", "reward", "airdrop", "salary", "other"]

# Earn durations
EARN_DURATIONS = {1: 3.0, 3: 5.0, 6: 7.0, 12: 10.0}  # months: APY%
