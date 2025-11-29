import asyncio
import socket
import ssl
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional

import dns.asyncresolver
import httpx

from .models import CheckResult, DNSRecords, SSLInfo


async def resolve_dns(hostname: str) -> DNSRecords:
    resolver = dns.asyncresolver.Resolver()
    records: Dict[str, List[str]] = {"A": [], "AAAA": [], "CNAME": [], "MX": [], "NS": []}
    for record_type in records.keys():
        try:
            answers = await resolver.resolve(hostname, record_type)
            parsed: List[str] = []
            for answer in answers:
                text = answer.to_text()
                if record_type == "MX":
                    parsed.append(str(text))
                else:
                    parsed.append(text)
            records[record_type] = parsed
        except Exception:
            records[record_type] = []
    return DNSRecords(**records)


async def fetch_ssl_info(hostname: str, port: int = 443) -> Optional[SSLInfo]:
    async def _get_cert():
        context = ssl.create_default_context()
        try:
            with socket.create_connection((hostname, port), timeout=5) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    cert = ssock.getpeercert()
                    return cert
        except Exception:
            return None

    cert = await asyncio.to_thread(_get_cert)
    if not cert:
        return None

    issuer = None
    if "issuer" in cert:
        issuer = ", ".join("=".join(attr) for attrs in cert["issuer"] for attr in attrs)

    not_after = cert.get("notAfter")
    expires = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc) if not_after else None
    now = datetime.now(timezone.utc)
    days_remaining = int((expires - now).total_seconds() // 86400) if expires else None
    hostname_matches = False
    try:
        ssl.match_hostname(cert, hostname)
        hostname_matches = True
    except Exception:
        hostname_matches = False

    valid = bool(expires and expires > now and hostname_matches)

    return SSLInfo(
        valid=valid,
        issuer=issuer,
        expires=expires,
        days_remaining=days_remaining,
        hostname_matches=hostname_matches,
    )


async def perform_check(url: str) -> CheckResult:
    timeout = httpx.Timeout(10.0)
    start = time.perf_counter()
    status_code: Optional[int] = None
    status_text = "ERROR"
    redirect_chain: List[str] = []
    final_url: Optional[str] = None
    ssl_info: Optional[SSLInfo] = None
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=timeout) as client:
            response = await client.get(url)
            status_code = response.status_code
            final_url = str(response.url)
            redirect_chain = [str(r.url) for r in response.history] + [final_url]
            if 200 <= status_code < 300:
                status_text = "UP"
            elif 300 <= status_code < 400:
                status_text = "REDIRECT"
            elif status_code >= 400:
                status_text = "DOWN"
            else:
                status_text = "ERROR"
    except httpx.ReadTimeout:
        status_text = "TIMEOUT"
    except httpx.ConnectError:
        status_text = "DOWN"
    except httpx.HTTPError as exc:
        status_text = "SSL ERROR" if "ssl" in str(exc).lower() else "ERROR"
    finally:
        duration_ms = int((time.perf_counter() - start) * 1000)

    dns_records: Optional[DNSRecords] = None
    hostname = None
    try:
        hostname = httpx.URL(url).host
    except Exception:
        hostname = None

    if hostname:
        dns_records = await resolve_dns(hostname)
        if url.startswith("https"):
            ssl_info = await fetch_ssl_info(hostname)

    return CheckResult(
        status_code=status_code,
        status_text=status_text,
        response_time_ms=duration_ms,
        final_url=final_url,
        redirect_chain=redirect_chain,
        ssl=ssl_info,
        dns=dns_records,
        timestamp=datetime.now(timezone.utc),
    )
