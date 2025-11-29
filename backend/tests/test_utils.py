import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import httpx
import pytest
import respx

from app.utils import fetch_ssl_info, perform_check, resolve_dns


@pytest.mark.asyncio
async def test_perform_check_up():
    url = "https://example.com"
    route = respx.Route("GET", url).mock(
        return_value=httpx.Response(200, request=httpx.Request("GET", url), json={})
    )
    async with respx.mock(base_url="https://example.com"):
        respx.get("/").mock(return_value=httpx.Response(200, request=httpx.Request("GET", url)))
        result = await perform_check(url)
    assert result.status_text == "UP"
    assert result.status_code == 200
    assert result.redirect_chain[-1] == url


@pytest.mark.asyncio
async def test_fetch_ssl_info_parses_cert():
    fake_cert = {
        "notAfter": "Dec 31 23:59:59 2099 GMT",
        "issuer": ((('commonName', 'Test CA'),),),
        "subject": ((('commonName', 'example.com'),),),
    }
    with patch("app.utils.asyncio.to_thread", AsyncMock(return_value=fake_cert)):
        info = await fetch_ssl_info("example.com")
    assert info
    assert info.issuer == "commonName=Test CA"
    assert info.days_remaining and info.days_remaining > 0
    assert info.hostname_matches is True or info.hostname_matches is False


@pytest.mark.asyncio
async def test_resolve_dns_handles_records():
    class FakeAnswer:
        def __init__(self, text):
            self._text = text

        def to_text(self):
            return self._text

    async def fake_resolve(host, record_type):
        values = {
            "A": [FakeAnswer("1.1.1.1")],
            "AAAA": [FakeAnswer("::1")],
            "CNAME": [],
            "MX": [FakeAnswer("10 mail.example.com")],
            "NS": [FakeAnswer("ns.example.com")],
        }
        return values.get(record_type, [])

    with patch("dns.asyncresolver.Resolver.resolve", side_effect=fake_resolve):
        records = await resolve_dns("example.com")
    assert records.A == ["1.1.1.1"]
    assert "mail.example.com" in records.MX[0]


@pytest.mark.asyncio
async def test_perform_check_timeout():
    async def slow_get(request):
        raise httpx.ReadTimeout("timeout")

    with respx.mock(base_url="https://slow.test") as mock:
        mock.get("/").mock(side_effect=httpx.ReadTimeout("timeout"))
        result = await perform_check("https://slow.test")
    assert result.status_text == "TIMEOUT"
