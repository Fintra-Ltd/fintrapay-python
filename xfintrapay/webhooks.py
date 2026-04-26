"""Webhook signature verification helper for the v2 webhook envelope."""

import hashlib
import hmac
import time
from datetime import datetime, timezone


def verify_webhook_signature(
    raw_body,
    signature: str,
    webhook_secret: str,
    timestamp: str = None,
    max_age_seconds: int = 300,
) -> bool:
    """
    Verify an FintraPay v2 webhook signature.

    The v2 envelope signs ``timestamp + "\\n" + raw_body`` with HMAC-SHA256.
    This helper recomputes that signature and compares constant-time. It also
    rejects deliveries older (or further in the future) than ``max_age_seconds``
    so a leaked signature can't be replayed indefinitely.

    Args:
        raw_body: The raw request body bytes (do NOT parse JSON first).
        signature: The X-FintraPay-Signature header value.
        webhook_secret: Your webhook secret from the dashboard.
        timestamp: The X-FintraPay-Timestamp header value (RFC3339 string).
            Required for v2 webhooks. Pass ``None`` only when verifying a
            legacy v1 delivery (raw-body signing) — not recommended.
        max_age_seconds: Reject deliveries older than this. Default 5 minutes.

    Returns:
        True if signature is valid AND timestamp is within ``max_age_seconds``.

    Usage (Flask):
        @app.route("/webhook", methods=["POST"])
        def webhook():
            sig = request.headers.get("X-FintraPay-Signature", "")
            ts  = request.headers.get("X-FintraPay-Timestamp", "")
            if not verify_webhook_signature(request.data, sig, WEBHOOK_SECRET, timestamp=ts):
                return "Invalid signature", 401
            data = request.json
            # process webhook...

    Usage (FastAPI):
        @app.post("/webhook")
        async def webhook(request: Request):
            body = await request.body()
            sig  = request.headers.get("X-FintraPay-Signature", "")
            ts   = request.headers.get("X-FintraPay-Timestamp", "")
            if not verify_webhook_signature(body, sig, WEBHOOK_SECRET, timestamp=ts):
                raise HTTPException(401)
            data = json.loads(body)
            # process webhook...
    """
    if not raw_body or not signature or not webhook_secret:
        return False

    if isinstance(raw_body, str):
        raw_body = raw_body.encode()

    # Freshness check (defeats replay).
    if timestamp:
        try:
            ts = datetime.fromisoformat(timestamp.replace("Z", "+00:00")).timestamp()
        except ValueError:
            # Fall back to integer seconds — some legacy clients may send that.
            try:
                ts = float(timestamp)
            except ValueError:
                return False
        if abs(time.time() - ts) > max_age_seconds:
            return False
        # v2 signing: HMAC over (timestamp + "\n" + raw_body).
        msg = timestamp.encode() + b"\n" + raw_body
    else:
        # Legacy v1 fallback — body-only. Discouraged; v2 deliveries will fail this path.
        msg = raw_body

    expected = hmac.new(webhook_secret.encode(), msg, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
