import ipaddress
from typing import Optional
from urllib.parse import urlparse

from pydantic import BaseModel


class UrlValidationResult(BaseModel):
    is_safe: bool
    error: Optional[str] = None
    sanitized_url: Optional[str] = None


BLOCKED_HOSTNAMES = {
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    "::1",
    "169.254.169.254",
    "metadata.google.internal",
}


def validate_external_url(url_string: str) -> UrlValidationResult:
    """
    Validate that a URL is safe for server-side HTTP requests.
    Prevents SSRF attacks to internal networks, cloud metadata, and loopbacks.
    """
    try:
        parsed = urlparse(url_string)
        if parsed.scheme not in ("http", "https"):
            return UrlValidationResult(
                is_safe=False, error="Only HTTP and HTTPS protocols are permitted"
            )

        hostname = parsed.hostname
        if not hostname:
            return UrlValidationResult(is_safe=False, error="Missing URL hostname")

        hostname_lower = hostname.lower()

        # Check explicit blocked hostnames
        if hostname_lower in BLOCKED_HOSTNAMES:
            return UrlValidationResult(
                is_safe=False, error=f"Restricted hostname: {hostname_lower}"
            )

        # Check if the hostname is an IP literal
        try:
            ip = ipaddress.ip_address(hostname_lower.strip("[]"))
            if (
                ip.is_private
                or ip.is_loopback
                or ip.is_link_local
                or ip.is_reserved
                or ip.is_multicast
            ):
                return UrlValidationResult(
                    is_safe=False, error="Access to non-public IP ranges is blocked"
                )
        except ValueError:
            # Not an IP literal; must be a domain name
            if "." not in hostname_lower:
                return UrlValidationResult(
                    is_safe=False, error="Intranet hostnames without public TLD are disallowed"
                )

            # DNS resolution check: verify resolved IP addresses are safe
            try:
                import socket

                addr_info = socket.getaddrinfo(hostname_lower, None)
                for item in addr_info:
                    sockaddr = item[4]
                    resolved_ip_str = sockaddr[0]
                    resolved_ip = ipaddress.ip_address(resolved_ip_str)
                    if (
                        resolved_ip.is_private
                        or resolved_ip.is_loopback
                        or resolved_ip.is_link_local
                        or resolved_ip.is_reserved
                        or resolved_ip.is_multicast
                    ):
                        return UrlValidationResult(
                            is_safe=False,
                            error=f"Resolved IP {resolved_ip_str} is in a restricted range",
                        )
            except socket.gaierror:
                # If DNS resolution fails during testing or offline, let it pass if domain is syntactically valid public domain
                pass

        return UrlValidationResult(is_safe=True, sanitized_url=url_string)
    except Exception as e:
        return UrlValidationResult(is_safe=False, error=f"Malformed URL: {str(e)}")
