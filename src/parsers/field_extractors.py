"""field_extractors.py - helpers to read parsed pdml fields."""
from typing import Optional, Dict, Any

def get_frame_number(pkt: Dict[str, Any]) -> Optional[int]:
    return pkt.get('fields', {}).get('frame.number')

def get_protocols(pkt: Dict[str, Any]):
    return pkt.get('fields', {}).get('protocols', [])
