from functools import lru_cache
from typing import Optional

from supabase import Client, create_client

from app.config import settings


@lru_cache(maxsize=1)
def get_client() -> Optional[Client]:
    """Singleton del cliente Supabase. Usa service key (acceso completo, solo backend).
    
    Devuelve None si las credenciales son placeholders (para testing sin DB).
    """
    # Skip if using placeholder credentials
    if not settings.supabase_url or "placeholder" in settings.supabase_url.lower():
        return None
    if not settings.supabase_service_key or settings.supabase_service_key == "eyJplaceholder":
        return None
    
    return create_client(settings.supabase_url, settings.supabase_service_key)