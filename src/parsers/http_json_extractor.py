"""http_json_extractor.py - detect and extract JSON HTTP bodies."""
import json
from typing import Optional, Dict, Any

def extract_http_json(payload_bytes: bytes) -> Optional[Dict[str, Any]]:
    try:
        text = payload_bytes.decode('utf-8', errors='strict')
        return json.loads(text)
    except Exception:
        return None
