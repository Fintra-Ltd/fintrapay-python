# fintrapay-python

Official Python SDK for the [FintraPay](https://fintrapay.io) crypto payment gateway API. Accept stablecoin payments, payment links, subscriptions, deposit API, payouts, withdrawals, and earn yield -- all with automatic HMAC-SHA256 request signing.

[![Version](https://img.shields.io/badge/version-0.1.0-blue.svg)](https://pypi.org/project/fintrapay/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)

---

## Installation

```bash
pip install fintrapay
```

## Quick Start

### Create an Invoice

```python
from xfintrapay import FintraPay

client = FintraPay(
    api_key="xfp_key_your_api_key",
    api_secret="xfp_secret_your_api_secret",
)

# Single-token invoice
invoice = client.create_invoice(
    amount="100.00",
    currency="USDT",
    blockchain="tron",
)
print(f"Payment address: {invoice['payment_address']}")
print(f"Invoice ID: {invoice['id']}")

# Multi-token invoice (customer chooses at checkout)
invoice = client.create_invoice(
    amount="250.00",
    accepted_tokens=["USDT", "USDC"],
    accepted_chains=["tron", "bsc", "ethereum"],
)
```

### Verify a Webhook

```python
from xfintrapay.webhooks import verify_webhook_signature

# Flask
@app.route("/webhook", methods=["POST"])
def webhook():
    sig = request.headers.get("X-FintraPay-Signature", "")
    if not verify_webhook_signature(request.data, sig, WEBHOOK_SECRET):
        return "Invalid signature", 401

    event = request.json
    if event["type"] == "invoice.paid":
        print(f"Invoice {event['data']['id']} paid!")
    return "OK", 200
```

## API Reference

All methods are available on the `FintraPay` client instance. HMAC-SHA256 signing is handled automatically.

### Invoices

| Method | Description |
|--------|-------------|
| `create_invoice(amount, currency, blockchain, ...)` | Create a payment invoice |
| `get_invoice(invoice_id)` | Get invoice by ID |
| `list_invoices(status, blockchain, currency, ...)` | List invoices with filters |

### Payouts

| Method | Description |
|--------|-------------|
| `create_payout(to_address, amount, currency, blockchain, ...)` | Create a single payout |
| `create_batch_payout(currency, blockchain, recipients)` | Create a batch payout |
| `get_payout(payout_id)` | Get payout by ID |
| `list_payouts(status, page, page_size)` | List payouts with filters |
| `list_batch_payouts(page, page_size)` | List batch payouts |
| `get_batch_payout(batch_id)` | Get batch payout details |

### Withdrawals

| Method | Description |
|--------|-------------|
| `create_withdrawal(amount, currency, blockchain)` | Withdraw to your registered wallet |
| `get_withdrawal(withdrawal_id)` | Get withdrawal by ID |
| `list_withdrawals(page, page_size)` | List withdrawals |

### Earn

| Method | Description |
|--------|-------------|
| `create_earn_contract(amount, currency, blockchain, duration_months)` | Create an Earn contract |
| `get_earn_contract(contract_id)` | Get Earn contract by ID |
| `list_earn_contracts(status, page)` | List Earn contracts |
| `withdraw_earn_interest(contract_id, amount)` | Withdraw accrued interest (min $10) |
| `break_earn_contract(contract_id)` | Early-break an Earn contract |
| `get_interest_history(contract_id)` | Get daily interest accrual history |

### Refunds

| Method | Description |
|--------|-------------|
| `create_refund(invoice_id, amount, to_address, reason, ...)` | Create a refund for a paid invoice |
| `get_refund(refund_id)` | Get refund by ID |
| `list_refunds(status, page, page_size)` | List all refunds |
| `list_invoice_refunds(invoice_id)` | List refunds for a specific invoice |

### Payment Links

| Method | Description |
|--------|-------------|
| `create_payment_link(title, slug, amount, ...)` | Create a reusable payment link |
| `list_payment_links(status, page, page_size)` | List payment links with filters |
| `get_payment_link(link_id)` | Get payment link by ID |
| `update_payment_link(link_id, **kwargs)` | Update a payment link |

### Subscription Plans

| Method | Description |
|--------|-------------|
| `create_subscription_plan(name, amount, interval, ...)` | Create a subscription plan |
| `list_subscription_plans(status, page, page_size)` | List subscription plans |
| `get_subscription_plan(plan_id)` | Get plan by ID |
| `update_subscription_plan(plan_id, **kwargs)` | Update a subscription plan |

### Subscriptions

| Method | Description |
|--------|-------------|
| `create_subscription(plan_id, customer_email, ...)` | Create a subscription |
| `list_subscriptions(status, plan_id, page, page_size)` | List subscriptions with filters |
| `get_subscription(subscription_id)` | Get subscription with invoice history |
| `cancel_subscription(subscription_id, reason)` | Cancel a subscription |
| `pause_subscription(subscription_id)` | Pause an active subscription |
| `resume_subscription(subscription_id)` | Resume a paused subscription |

### Deposit API

| Method | Description |
|--------|-------------|
| `create_deposit_user(external_user_id, email, label)` | Register end user for deposits |
| `get_deposit_user(external_user_id)` | Get user with addresses and balances |
| `list_deposit_users(page, page_size)` | List deposit users |
| `update_deposit_user(external_user_id, **kwargs)` | Update user (email, label, is_active, is_blocked) |
| `create_deposit_address(external_user_id, blockchain)` | Generate address for a chain |
| `create_all_deposit_addresses(external_user_id)` | Generate addresses for all 7 chains |
| `list_deposit_addresses(external_user_id)` | List all addresses for a user |
| `list_deposits(external_user_id, token, blockchain, status)` | List deposit events |
| `get_deposit(deposit_id)` | Get single deposit detail |
| `list_deposit_balances(external_user_id)` | Get per-token per-chain balances |

### Balance & Fees

| Method | Description |
|--------|-------------|
| `get_balance()` | Get custodial balances across all chains |
| `estimate_fees(amount, currency, blockchain)` | Estimate transaction fees |

### Support Tickets

| Method | Description |
|--------|-------------|
| `create_ticket(subject, message, priority)` | Create a support ticket |
| `list_tickets(page, page_size)` | List support tickets |
| `get_ticket(ticket_id)` | Get ticket by ID |
| `reply_ticket(ticket_id, message)` | Reply to a support ticket |

## Error Handling

The SDK raises typed exceptions for different error scenarios:

```python
from xfintrapay import (
    FintraPay,
    FintraPayError,
    AuthenticationError,
    ValidationError,
    RateLimitError,
)

client = FintraPay(api_key="xfp_key_...", api_secret="xfp_secret_...")

try:
    invoice = client.create_invoice(amount="100.00", currency="USDT", blockchain="tron")
except AuthenticationError as e:
    # Invalid API key or secret (HTTP 401)
    print(f"Auth failed: {e.message}")
except ValidationError as e:
    # Invalid request parameters (HTTP 422)
    print(f"Validation error: {e.message}, details: {e.details}")
except RateLimitError as e:
    # Too many requests (HTTP 429)
    print(f"Rate limited. Retry after {e.retry_after} seconds")
except FintraPayError as e:
    # Any other API error
    print(f"API error ({e.status}): {e.message}")
```

## Webhook Verification

Always verify webhook signatures before processing events. Use the raw request body -- do NOT parse JSON first.

### Flask

```python
from xfintrapay.webhooks import verify_webhook_signature

@app.route("/webhook", methods=["POST"])
def webhook():
    sig = request.headers.get("X-FintraPay-Signature", "")
    if not verify_webhook_signature(request.data, sig, WEBHOOK_SECRET):
        return "Invalid signature", 401
    event = request.json
    # process event...
    return "OK", 200
```

### Django

```python
from xfintrapay.webhooks import verify_webhook_signature

def webhook_view(request):
    sig = request.META.get("HTTP_X_FINTRAPAY_SIGNATURE", "")
    if not verify_webhook_signature(request.body, sig, WEBHOOK_SECRET):
        return HttpResponse(status=401)
    data = json.loads(request.body)
    # process event...
    return HttpResponse("OK")
```

### FastAPI

```python
from xfintrapay.webhooks import verify_webhook_signature

@app.post("/webhook")
async def webhook(request: Request):
    body = await request.body()
    sig = request.headers.get("X-FintraPay-Signature", "")
    if not verify_webhook_signature(body, sig, WEBHOOK_SECRET):
        raise HTTPException(status_code=401)
    data = json.loads(body)
    # process event...
    return {"received": True}
```

## Supported Chains & Tokens

7 blockchains: TRON, BSC, Ethereum, Solana, Base, Arbitrum, Polygon

6 stablecoins: USDT, USDC, DAI, FDUSD, TUSD, PYUSD

## Links

- [FintraPay Homepage](https://fintrapay.io)
- [API Documentation](https://fintrapay.io/docs)
- [GitHub Repository](https://github.com/Fintra-Ltd/fintrapay-python)

## License

MIT License. See [LICENSE](LICENSE) for details.
