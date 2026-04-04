"""FintraPay API client with automatic HMAC-SHA256 signing."""

import hashlib
import hmac
import json
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import requests


class FintraPayError(Exception):
    """Base exception for FintraPay SDK."""

    def __init__(self, message: str, code: str = "", status: int = 0, details: dict = None):
        self.message = message
        self.code = code
        self.status = status
        self.details = details or {}
        super().__init__(message)


class ValidationError(FintraPayError):
    """Raised when request validation fails (422)."""
    pass


class AuthenticationError(FintraPayError):
    """Raised when API authentication fails (401)."""
    pass


class RateLimitError(FintraPayError):
    """Raised when rate limit is exceeded (429)."""

    def __init__(self, message: str, retry_after: int = 0, **kwargs):
        self.retry_after = retry_after
        super().__init__(message, **kwargs)


class FintraPay:
    """
    FintraPay API client.

    Handles HMAC-SHA256 request signing automatically.

    Usage:
        client = FintraPay(api_key="xfp_key_...", api_secret="xfp_secret_...")
        invoice = client.create_invoice(amount="100.00", currency="USDT", blockchain="tron")
    """

    DEFAULT_BASE_URL = "https://fintrapay.io/v1"

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        base_url: str = None,
        timeout: int = 30,
    ):
        if not api_key or not api_secret:
            raise ValueError("api_key and api_secret are required")

        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = (base_url or self.DEFAULT_BASE_URL).rstrip("/")
        self.timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({"Content-Type": "application/json"})

    # ── Request signing ──────────────────────────────────────────

    def _sign(self, method: str, path: str, body: str = "") -> Dict[str, str]:
        timestamp = str(int(time.time()))
        payload = f"{timestamp}\n{method}\n{path}\n{body}"
        signature = hmac.new(
            self.api_secret.encode(), payload.encode(), hashlib.sha256
        ).hexdigest()
        return {
            "X-API-Key": self.api_key,
            "X-Timestamp": timestamp,
            "X-Signature": signature,
        }

    def _request(self, method: str, path: str, data: dict = None) -> Any:
        url = f"{self.base_url}{path}"
        body = json.dumps(data, separators=(",", ":")) if data else ""
        headers = self._sign(method.upper(), path, body)

        response = self._session.request(
            method=method,
            url=url,
            data=body if body else None,
            headers=headers,
            timeout=self.timeout,
        )

        return self._handle_response(response)

    def _handle_response(self, response: requests.Response) -> Any:
        if response.status_code == 204:
            return None

        try:
            data = response.json()
        except ValueError:
            data = {"error": response.text}

        if response.ok:
            return data

        error_msg = data.get("error", "Unknown error")
        error_code = data.get("code", "")
        details = data.get("details", {})

        if response.status_code == 401:
            raise AuthenticationError(error_msg, code=error_code, status=401)
        elif response.status_code == 422:
            raise ValidationError(error_msg, code=error_code, status=422, details=details)
        elif response.status_code == 429:
            retry = int(response.headers.get("Retry-After", 60))
            raise RateLimitError(error_msg, retry_after=retry, code=error_code, status=429)
        else:
            raise FintraPayError(error_msg, code=error_code, status=response.status_code, details=details)

    # ── Invoices ─────────────────────────────────────────────────

    def create_invoice(
        self,
        amount: str,
        currency: str = None,
        blockchain: str = None,
        mode: str = "custodial",
        accepted_tokens: List[str] = None,
        accepted_chains: List[str] = None,
        external_id: str = None,
        expiry_minutes: int = None,
        expires_at: str = None,
        success_url: str = None,
        cancel_url: str = None,
    ) -> dict:
        """
        Create a payment invoice.

        Single token:
            create_invoice(amount="100", currency="USDT", blockchain="tron")

        Multi-token (customer chooses on checkout):
            create_invoice(amount="100", accepted_tokens=["USDT","USDC"], accepted_chains=["tron","bsc"])

        All tokens (customer chooses everything):
            create_invoice(amount="100")
        """
        body = {"amount": str(amount), "mode": mode}
        if currency:
            body["currency"] = currency
        if blockchain:
            body["blockchain"] = blockchain
        if accepted_tokens:
            body["accepted_tokens"] = accepted_tokens
        if accepted_chains:
            body["accepted_chains"] = accepted_chains
        if external_id:
            body["external_id"] = external_id
        if expiry_minutes:
            body["expiry_minutes"] = expiry_minutes
        if expires_at:
            body["expires_at"] = expires_at
        if success_url:
            body["success_url"] = success_url
        if cancel_url:
            body["cancel_url"] = cancel_url
        return self._request("POST", "/invoices", body)

    def get_invoice(self, invoice_id: str) -> dict:
        """Get invoice by ID."""
        return self._request("GET", f"/invoices/{invoice_id}")

    def list_invoices(
        self,
        status: str = None,
        blockchain: str = None,
        currency: str = None,
        mode: str = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """List invoices with filters."""
        params = [f"page={page}", f"page_size={page_size}"]
        if status:
            params.append(f"status={status}")
        if blockchain:
            params.append(f"blockchain={blockchain}")
        if currency:
            params.append(f"currency={currency}")
        if mode:
            params.append(f"mode={mode}")
        return self._request("GET", f"/invoices?{'&'.join(params)}")

    # ── Payouts ──────────────────────────────────────────────────

    def create_payout(
        self,
        to_address: str,
        amount: str,
        currency: str,
        blockchain: str,
        reason: str = "payment",
        reference: str = None,
    ) -> dict:
        """Create a single payout to any address."""
        body = {
            "to_address": to_address,
            "amount": str(amount),
            "currency": currency,
            "blockchain": blockchain,
            "reason": reason,
        }
        if reference:
            body["reference"] = reference
        return self._request("POST", "/payouts", body)

    def create_batch_payout(
        self,
        currency: str,
        blockchain: str,
        recipients: List[dict],
    ) -> dict:
        """
        Create a batch payout.

        recipients: [{"to_address": "0x...", "amount": "50.00", "reference": "sal-001"}, ...]
        """
        return self._request("POST", "/payouts/batch", {
            "currency": currency,
            "blockchain": blockchain,
            "recipients": recipients,
        })

    def get_payout(self, payout_id: str) -> dict:
        """Get payout by ID."""
        return self._request("GET", f"/payouts/{payout_id}")

    def list_payouts(self, status: str = None, page: int = 1, page_size: int = 20) -> dict:
        """List payouts."""
        params = [f"page={page}", f"page_size={page_size}"]
        if status:
            params.append(f"status={status}")
        return self._request("GET", f"/payouts?{'&'.join(params)}")

    # ── Withdrawals ──────────────────────────────────────────────

    def create_withdrawal(self, amount: str, currency: str, blockchain: str) -> dict:
        """Withdraw to your registered wallet."""
        return self._request("POST", "/withdrawals", {
            "amount": str(amount),
            "currency": currency,
            "blockchain": blockchain,
        })

    def get_withdrawal(self, withdrawal_id: str) -> dict:
        """Get withdrawal by ID."""
        return self._request("GET", f"/withdrawals/{withdrawal_id}")

    def list_withdrawals(self, page: int = 1, page_size: int = 20) -> dict:
        """List withdrawals."""
        return self._request("GET", f"/withdrawals?page={page}&page_size={page_size}")

    # ── Earn ─────────────────────────────────────────────────────

    def create_earn_contract(
        self, amount: str, currency: str, blockchain: str, duration_months: int
    ) -> dict:
        """Create an Earn contract."""
        return self._request("POST", "/earn/contracts", {
            "amount": str(amount),
            "currency": currency,
            "blockchain": blockchain,
            "duration_months": duration_months,
        })

    def get_earn_contract(self, contract_id: str) -> dict:
        """Get Earn contract by ID."""
        return self._request("GET", f"/earn/contracts/{contract_id}")

    def list_earn_contracts(self, status: str = None, page: int = 1) -> dict:
        """List Earn contracts."""
        params = [f"page={page}"]
        if status:
            params.append(f"status={status}")
        return self._request("GET", f"/earn/contracts?{'&'.join(params)}")

    def withdraw_earn_interest(self, contract_id: str, amount: str) -> dict:
        """Withdraw accrued interest (min $10)."""
        return self._request("POST", f"/earn/contracts/{contract_id}/withdraw-interest", {
            "amount": str(amount),
        })

    def break_earn_contract(self, contract_id: str) -> dict:
        """Early break an Earn contract."""
        return self._request("POST", f"/earn/contracts/{contract_id}/break")

    # ── Refunds ───────────────────────────────────────────────────

    def create_refund(
        self,
        invoice_id: str,
        amount: str,
        to_address: str,
        reason: str,
        customer_email: str = None,
    ) -> dict:
        """
        Create a refund for a paid invoice.

        Partial refunds supported — multiple refunds per invoice until
        the total refunded equals the invoice amount.

        Args:
            invoice_id: The invoice to refund.
            amount: Refund amount in the invoice's currency.
            to_address: Customer's wallet address to receive the refund.
            reason: Explanation for the refund.
            customer_email: Optional customer email for notification.

        Statuses: pending → processing → completed | rejected
        """
        body = {
            "amount": str(amount),
            "to_address": to_address,
            "reason": reason,
        }
        if customer_email:
            body["customer_email"] = customer_email
        return self._request("POST", f"/invoices/{invoice_id}/refunds", body)

    def get_refund(self, refund_id: str) -> dict:
        """Get a refund by ID."""
        return self._request("GET", f"/refunds/{refund_id}")

    def list_refunds(self, status: str = None, page: int = 1, page_size: int = 20) -> dict:
        """List all refunds."""
        params = [f"page={page}", f"page_size={page_size}"]
        if status:
            params.append(f"status={status}")
        return self._request("GET", f"/refunds?{'&'.join(params)}")

    def list_invoice_refunds(self, invoice_id: str) -> dict:
        """List all refunds for a specific invoice."""
        return self._request("GET", f"/invoices/{invoice_id}/refunds")

    # ── Balance ──────────────────────────────────────────────────

    def get_balance(self) -> dict:
        """Get custodial balances across all chains."""
        return self._request("GET", "/balance")

    # ── Batch Payouts ───────────────────────────────────────────

    def list_batch_payouts(self, page: int = 1, page_size: int = 20) -> dict:
        """List batch payouts."""
        return self._request("GET", f"/payouts/batches?page={page}&page_size={page_size}")

    def get_batch_payout(self, batch_id: str) -> dict:
        """Get batch payout details with all items."""
        return self._request("GET", f"/payouts/batches/{batch_id}")

    # ── Fees ────────────────────────────────────────────────────

    def estimate_fees(self, amount: str, currency: str, blockchain: str) -> dict:
        """Estimate transaction fees."""
        return self._request("POST", "/fees/estimate", {
            "amount": str(amount),
            "currency": currency,
            "blockchain": blockchain,
        })

    # ── Tickets ─────────────────────────────────────────────────

    def create_ticket(self, subject: str, message: str, priority: str = "medium") -> dict:
        """Create a support ticket."""
        return self._request("POST", "/tickets", {
            "subject": subject,
            "message": message,
            "priority": priority,
        })

    def list_tickets(self, page: int = 1, page_size: int = 20) -> dict:
        """List support tickets."""
        return self._request("GET", f"/tickets?page={page}&page_size={page_size}")

    def get_ticket(self, ticket_id: str) -> dict:
        """Get support ticket by ID."""
        return self._request("GET", f"/tickets/{ticket_id}")

    def reply_ticket(self, ticket_id: str, message: str) -> dict:
        """Reply to a support ticket."""
        return self._request("POST", f"/tickets/{ticket_id}/reply", {
            "message": message,
        })

    # ── Earn History ────────────────────────────────────────────

    def get_interest_history(self, contract_id: str) -> dict:
        """Get daily interest accrual history for an Earn contract."""
        return self._request("GET", f"/earn/contracts/{contract_id}/interest-history")

    # ── Payment Links ──────────────────────────────────────────

    def create_payment_link(self, title: str, slug: str = None, amount: str = None,
                            fixed_amount: bool = True, description: str = None,
                            min_amount: str = None, max_amount: str = None,
                            success_url: str = None, cancel_url: str = None, **kwargs) -> dict:
        """Create a reusable payment link."""
        data = {"title": title, "fixed_amount": fixed_amount}
        if slug: data["slug"] = slug
        if amount: data["amount"] = str(amount)
        if description: data["description"] = description
        if min_amount: data["min_amount"] = str(min_amount)
        if max_amount: data["max_amount"] = str(max_amount)
        if success_url: data["success_url"] = success_url
        if cancel_url: data["cancel_url"] = cancel_url
        data.update(kwargs)
        return self._request("POST", "/payment-links", data)

    def list_payment_links(self, status: str = None, page: int = 1, page_size: int = 20) -> dict:
        """List payment links."""
        q = f"/payment-links?page={page}&page_size={page_size}"
        if status: q += f"&status={status}"
        return self._request("GET", q)

    def get_payment_link(self, link_id: str) -> dict:
        """Get payment link by ID."""
        return self._request("GET", f"/payment-links/{link_id}")

    def update_payment_link(self, link_id: str, **kwargs) -> dict:
        """Update a payment link (title, amount, status, etc.)."""
        return self._request("PATCH", f"/payment-links/{link_id}", kwargs)

    # ── Subscription Plans ─────────────────────────────────────

    def create_subscription_plan(self, name: str, amount: str, interval: str = "monthly",
                                  slug: str = None, trial_days: int = 0,
                                  description: str = None, **kwargs) -> dict:
        """Create a subscription plan."""
        data = {"name": name, "amount": str(amount), "interval": interval, "trial_days": trial_days}
        if slug: data["slug"] = slug
        if description: data["description"] = description
        data.update(kwargs)
        return self._request("POST", "/subscription-plans", data)

    def list_subscription_plans(self, status: str = None, page: int = 1, page_size: int = 20) -> dict:
        """List subscription plans."""
        q = f"/subscription-plans?page={page}&page_size={page_size}"
        if status: q += f"&status={status}"
        return self._request("GET", q)

    def get_subscription_plan(self, plan_id: str) -> dict:
        """Get subscription plan by ID."""
        return self._request("GET", f"/subscription-plans/{plan_id}")

    def update_subscription_plan(self, plan_id: str, **kwargs) -> dict:
        """Update a subscription plan."""
        return self._request("PATCH", f"/subscription-plans/{plan_id}", kwargs)

    # ── Subscriptions ──────────────────────────────────────────

    def create_subscription(self, plan_id: str, customer_email: str,
                            customer_name: str = None, external_id: str = None) -> dict:
        """Create a subscription for a customer."""
        data = {"plan_id": plan_id, "customer_email": customer_email}
        if customer_name: data["customer_name"] = customer_name
        if external_id: data["external_id"] = external_id
        return self._request("POST", "/subscriptions", data)

    def list_subscriptions(self, status: str = None, plan_id: str = None,
                           page: int = 1, page_size: int = 20) -> dict:
        """List subscriptions."""
        q = f"/subscriptions?page={page}&page_size={page_size}"
        if status: q += f"&status={status}"
        if plan_id: q += f"&plan_id={plan_id}"
        return self._request("GET", q)

    def get_subscription(self, subscription_id: str) -> dict:
        """Get subscription detail with invoice history."""
        return self._request("GET", f"/subscriptions/{subscription_id}")

    def cancel_subscription(self, subscription_id: str, reason: str = None) -> dict:
        """Cancel a subscription."""
        data = {}
        if reason: data["reason"] = reason
        return self._request("POST", f"/subscriptions/{subscription_id}/cancel", data)

    def pause_subscription(self, subscription_id: str) -> dict:
        """Pause a subscription."""
        return self._request("POST", f"/subscriptions/{subscription_id}/pause", {})

    def resume_subscription(self, subscription_id: str) -> dict:
        """Resume a paused subscription."""
        return self._request("POST", f"/subscriptions/{subscription_id}/resume", {})

    # ── Deposit API ────────────────────────────────────────────

    def create_deposit_user(self, external_user_id: str, email: str = None,
                            label: str = None, **kwargs) -> dict:
        """Register a merchant-side end user for deposits."""
        data = {"external_user_id": external_user_id}
        if email: data["email"] = email
        if label: data["label"] = label
        data.update(kwargs)
        return self._request("POST", "/deposit-api/users", data)

    def get_deposit_user(self, external_user_id: str) -> dict:
        """Get deposit user with addresses and balances."""
        return self._request("GET", f"/deposit-api/users/{external_user_id}")

    def list_deposit_users(self, page: int = 1, page_size: int = 20) -> dict:
        """List deposit API users."""
        return self._request("GET", f"/deposit-api/users?page={page}&page_size={page_size}")

    def update_deposit_user(self, external_user_id: str, **kwargs) -> dict:
        """Update a deposit user (email, label, is_active, is_blocked)."""
        return self._request("PATCH", f"/deposit-api/users/{external_user_id}", kwargs)

    def create_deposit_address(self, external_user_id: str, blockchain: str) -> dict:
        """Generate a deposit address for a user on a specific chain."""
        return self._request("POST", f"/deposit-api/users/{external_user_id}/addresses", {"blockchain": blockchain})

    def create_all_deposit_addresses(self, external_user_id: str) -> dict:
        """Generate deposit addresses for all 7 chains at once."""
        return self._request("POST", f"/deposit-api/users/{external_user_id}/addresses/all", {})

    def list_deposit_addresses(self, external_user_id: str) -> dict:
        """List all deposit addresses for a user."""
        return self._request("GET", f"/deposit-api/users/{external_user_id}/addresses")

    def list_deposits(self, external_user_id: str = None, token: str = None,
                      blockchain: str = None, status: str = None,
                      page: int = 1, page_size: int = 20) -> dict:
        """List deposits. If external_user_id is provided, filters by user."""
        if external_user_id:
            q = f"/deposit-api/users/{external_user_id}/deposits?page={page}&page_size={page_size}"
        else:
            q = f"/deposit-api/deposits?page={page}&page_size={page_size}"
        if token: q += f"&token={token}"
        if blockchain: q += f"&blockchain={blockchain}"
        if status: q += f"&status={status}"
        return self._request("GET", q)

    def get_deposit(self, deposit_id: str) -> dict:
        """Get single deposit event detail."""
        return self._request("GET", f"/deposit-api/deposits/{deposit_id}")

    def list_deposit_balances(self, external_user_id: str) -> dict:
        """Get per-token per-chain balances for a deposit user."""
        return self._request("GET", f"/deposit-api/users/{external_user_id}/balances")
