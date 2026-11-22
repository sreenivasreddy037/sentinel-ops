import json

import pytest

from app.guardrails.pii_scrubber import scrub


@pytest.mark.parametrize("secret", [
    "AKIA" + "A" * 16,
    "ASIA" + "B" * 16,
    "192.168.10.20",
    "2001:db8::1",
    "::1",
    "::ffff:192.0.2.1",
    "fe80::1234%en0",
    "alice@example.test",
    "password=hunter2",
    'password="a secret with spaces"',
    "passwd: 'secret two'",
    "aws_secret_access_key=supersecret",
    "api_key=neverprint",
    "Authorization: Bearer hidden.jwt.value",
    "-----BEGIN PRIVATE KEY-----\nSECRET\n-----END PRIVATE KEY-----",
])
def test_redacts_sensitive_values(secret):
    result = scrub(f"Ticket: {secret}; code 0x80070005", use_presidio=False)
    assert secret not in result.text
    if secret.startswith("::ffff:"):
        assert "::ffff:" not in result.text
    assert "0x80070005" in result.text
    assert result.redaction_map
    assert secret not in json.dumps(result.redaction_map)


def test_scrubbing_is_idempotent_and_preserves_codes():
    first = scrub("HTTP 502 OOMKilled at 10.0.0.1 password=test", use_presidio=False)
    second = scrub(first.text, use_presidio=False)
    assert first.text == second.text
    assert "HTTP 502 OOMKilled" in second.text


def test_presidio_pattern_recognizer_needs_no_nlp_download():
    result = scrub("Call +1 405-555-0101; incident 0x80070005", use_presidio=True)
    assert "405-555-0101" not in result.text
    assert "0x80070005" in result.text
