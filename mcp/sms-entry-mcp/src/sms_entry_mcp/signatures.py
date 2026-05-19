"""Twilio request-signature verification.

Twilio signs each incoming webhook with HMAC-SHA1 of the URL + the
sorted POST parameters concatenated, base64-encoded, and delivered in
the ``X-Twilio-Signature`` header. See
https://www.twilio.com/docs/usage/webhooks/webhooks-security

This module is a pure function so it can be unit-tested against the
example vectors Twilio publishes in the security docs without needing
any network access.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
from typing import Mapping


def verify_twilio_signature(
    auth_token: str,
    url: str,
    params: Mapping[str, str],
    signature: str,
) -> bool:
    """Return True if the Twilio signature matches.

    Parameters
    ----------
    auth_token
        The Twilio account auth token (the shared HMAC key).
    url
        The full URL the webhook hit (scheme + host + path + query).
    params
        The POST form parameters Twilio sent. If the request was a
        GET (or you only have the raw body), pass ``{}`` and append
        the query string to ``url``.
    signature
        The value of the ``X-Twilio-Signature`` HTTP header.

    Notes
    -----
    Algorithm (from Twilio's docs):

    1. Take the full URL of the request (scheme + host + path + query).
    2. Sort the POST parameter keys alphabetically.
    3. Append each ``key + value`` pair to the URL string in sorted order.
    4. HMAC-SHA1 the resulting string with the auth token.
    5. Base64-encode the digest. Compare to the header in constant time.
    """
    if not auth_token or not signature:
        return False
    payload = url
    for key in sorted(params.keys()):
        payload += key + params[key]
    digest = hmac.new(
        auth_token.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha1,
    ).digest()
    expected = base64.b64encode(digest).decode("ascii")
    return hmac.compare_digest(expected, signature)


__all__ = ["verify_twilio_signature"]
