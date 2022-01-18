from typing import Optional

def get_safe_name(name: str) -> Optional[str]:
    if not name: return None

    return (name.lower()).replace(' ', '_')