"""
Shared slowapi Limiter — a separate module (not defined in main.py) so
route files can import and apply @limiter.limit(...) without a circular
import back to the app module.
"""
import ipaddress
from starlette.requests import Request
from slowapi import Limiter

TRUSTED_PROXIES = {"127.0.0.1", "::1", "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"}


def _is_trusted_proxy(ip_str: str) -> bool:
    if not ip_str:
        return False
    try:
        ip = ipaddress.ip_address(ip_str)
        for tp in TRUSTED_PROXIES:
            if "/" in tp:
                if ip in ipaddress.ip_network(tp):
                    return True
            elif ip_str == tp:
                return True
    except Exception:
        pass
    return False


def get_real_client_ip(request: Request) -> str:
    """
    Safely extract the real client IP address. Inspects X-Forwarded-For
    and X-Real-IP headers ONLY when the request's immediate client IP is a
    trusted reverse proxy.
    """
    remote_ip = request.client.host if request.client else "127.0.0.1"

    x_real_ip = request.headers.get("x-real-ip")
    x_forwarded_for = request.headers.get("x-forwarded-for")

    if x_real_ip and _is_trusted_proxy(remote_ip):
        return x_real_ip.strip()

    if x_forwarded_for and _is_trusted_proxy(remote_ip):
        forwarded_ips = [ip.strip() for ip in x_forwarded_for.split(",") if ip.strip()]
        if forwarded_ips:
            return forwarded_ips[0]

    return remote_ip


limiter = Limiter(key_func=get_real_client_ip)
