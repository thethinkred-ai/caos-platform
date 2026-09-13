"""Single rate-limiter instance (Track 0 leftover from the first audit).

main.py registers it on the app; routers import the same object for
their decorators — two instances would silently leave limits
unenforced.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
