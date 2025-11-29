from datetime import datetime
from typing import List, Literal, Optional
from pydantic import BaseModel, HttpUrl, Field


StatusText = Literal["UP", "DOWN", "REDIRECT", "TIMEOUT", "SSL ERROR", "ERROR"]


class SSLInfo(BaseModel):
    valid: bool
    issuer: Optional[str]
    expires: Optional[datetime]
    days_remaining: Optional[int]
    hostname_matches: Optional[bool]


class DNSRecords(BaseModel):
    A: List[str] = Field(default_factory=list)
    AAAA: List[str] = Field(default_factory=list)
    CNAME: List[str] = Field(default_factory=list)
    MX: List[str] = Field(default_factory=list)
    NS: List[str] = Field(default_factory=list)


class CheckResult(BaseModel):
    status_code: Optional[int]
    status_text: StatusText
    response_time_ms: Optional[int]
    final_url: Optional[str]
    redirect_chain: List[str] = Field(default_factory=list)
    ssl: Optional[SSLInfo]
    dns: Optional[DNSRecords]
    timestamp: datetime


class MonitoredURL(BaseModel):
    url: HttpUrl
    last_status: Optional[StatusText] = None
    last_response_time: Optional[int] = None
    uptime_percentage: Optional[float] = None


class HistoryResponse(BaseModel):
    url: HttpUrl
    checks: List[CheckResult]
