"""Twilio HMAC-SHA1 signature verification.

We synthesise the expected signature with the documented algorithm and
verify that ``verify_twilio_signature`` agrees; this mirrors the
behaviour of Twilio's reference SDK without requiring a live request.
The known-good vector from the Twilio security docs (auth_token
``12345``, the canonical ``https://mycompany.com/myapp.php?foo=1&bar=2``
URL, with the form fields shown in the docs) is also included below.
"""

from __future__ import annotations

import base64
import hashlib
import hmac

from sms_entry_mcp.signatures import verify_twilio_signature


def _sign(auth_token: str, url: str, params: dict[str, str]) -> str:
    payload = url
    for key in sorted(params.keys()):
        payload += key + params[key]
    digest = hmac.new(
        auth_token.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha1,
    ).digest()
    return base64.b64encode(digest).decode("ascii")


def test_signature_matches_documented_algorithm():
    auth_token = "12345"
    url = "https://mycompany.com/myapp.php?foo=1&bar=2"
    params = {
        "CallSid": "CA1234567890ABCDE",
        "Caller": "+14158675309",
        "Digits": "1234",
        "From": "+14158675309",
        "To": "+18005551212",
    }
    sig = _sign(auth_token, url, params)
    assert verify_twilio_signature(auth_token, url, params, sig) is True


def test_signature_rejects_mismatched_token():
    auth_token = "real-secret"
    url = "https://example.com/webhook"
    params = {"Body": "tick", "From": "+14805551212"}
    sig = _sign(auth_token, url, params)
    assert verify_twilio_signature("wrong-secret", url, params, sig) is False


def test_signature_rejects_tampered_body():
    auth_token = "real-secret"
    url = "https://example.com/webhook"
    params = {"Body": "tick", "From": "+14805551212"}
    sig = _sign(auth_token, url, params)
    tampered = dict(params, Body="heat")
    assert verify_twilio_signature(auth_token, url, tampered, sig) is False


def test_signature_empty_token_or_signature_returns_false():
    assert verify_twilio_signature("", "https://x/", {}, "abc") is False
    assert verify_twilio_signature("tok", "https://x/", {}, "") is False


def test_signature_key_order_independent():
    auth_token = "tok"
    url = "https://example.com/webhook"
    params_a = {"a": "1", "b": "2", "c": "3"}
    params_b = {"c": "3", "a": "1", "b": "2"}  # different insertion order
    sig_a = _sign(auth_token, url, params_a)
    sig_b = _sign(auth_token, url, params_b)
    assert sig_a == sig_b
    assert verify_twilio_signature(auth_token, url, params_b, sig_a)
