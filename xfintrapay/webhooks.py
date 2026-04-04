"""Webhook signature verification helper."""

import hashlib
import hmac


def verify_webhook_signature(
    raw_body: bytes,
    signature: str,
    webhook_secret: str,
) -> bool:
    """
    Verify an FintraPay webhook signature.

    Args:
        raw_body: The raw request body bytes (do NOT parse JSON first).
        signature: The X-FintraPay-Signature header value.
        webhook_secret: Your webhook secret from the dashboard.

    Returns:
        True if signature is valid, False otherwise.

    Usage (Flask):
        @app.route("/webhook", methods=["POST"])
        def webhook():
            sig = request.headers.get("X-FintraPay-Signature", "")
            if not verify_webhook_signature(request.data, sig, WEBHOOK_SECRET):
                return "Invalid signature", 401
            data = request.json
            # process webhook...

    Usage (Django):
        def webhook_view(request):
            sig = request.META.get("HTTP_X_FINTRAPAY_SIGNATURE", "")
            if not verify_webhook_signature(request.body, sig, WEBHOOK_SECRET):
                return HttpResponse(status=401)
            data = json.loads(request.body)
            # process webhook...

    Usage (FastAPI):
        @app.post("/webhook")
        async def webhook(request: Request):
            body = await request.body()
            sig = request.headers.get("X-FintraPay-Signature", "")
            if not verify_webhook_signature(body, sig, WEBHOOK_SECRET):
                raise HTTPException(401)
            data = json.loads(body)
            # process webhook...
    """
    if not raw_body or not signature or not webhook_secret:
        return False

    if isinstance(raw_body, str):
        raw_body = raw_body.encode()

    expected = hmac.new(
        webhook_secret.encode(), raw_body, hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected, signature)
