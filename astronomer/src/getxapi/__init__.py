"""GetXAPI Module — the ONLY way to interact with the X API.

Every API call in BEAR MUST go through this module.
No direct httpx calls to api.getxapi.com allowed.

Usage:
    from src.getxapi import GetXAPI
    
    api = GetXAPI()
    tweets = api.search(handle="Timeless_Crypto", since="2024-09-01", until="2024-09-08")
    api.status()
"""

from .client import GetXAPI
from .budget import BudgetController

__all__ = ["GetXAPI", "BudgetController"]
