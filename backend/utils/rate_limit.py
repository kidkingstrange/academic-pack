"""
Shared slowapi Limiter — a separate module (not defined in main.py) so
route files can import and apply @limiter.limit(...) without a circular
import back to the app module.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
