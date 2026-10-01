"""pdml_parser.py - parse PDML packet fragments into dicts (improved)."""
import xml.etree.ElementTree as ET

def parse_single_pdml_packet(xml_text: str) -> dict:
    """
    Parse PDML packet into structured dict.
    Extracts useful fields while EXCLUDING large payload data.
    """
    try:
        root = ET.fromstring(xml_text)
    except Exception:
        return None
    
    pkt = {}
    
    # Fields to EXCLUDE (too large)
    EXCLUDED_FIELDS = {
        'udp.payload',
        'tcp.payload', 
        'data.data',
        'data.text'
    }
    
    # -------- Frame fields --------
    frame = root.find(".//proto[@name='frame']")
    if frame is not None:
        for f in frame.findall("field"):
            name = f.get("name")
            show = f.get("show")
            if name and show:
                # Remove "frame." prefix to avoid redundancy
                field_name = name.replace("frame.", "")
                pkt[f"frame.{field_name}"] = show
    
    # -------- IP fields --------
    ip = root.find(".//proto[@name='ip']")
    if ip:
        for f in ip.findall("field"):
            name = f.get("name")
            show = f.get("show")
            if name and show:
                field_name = name.replace("ip.", "")
                pkt[f"ip.{field_name}"] = show
    
    # -------- UDP fields --------
    udp = root.find(".//proto[@name='udp']")
    if udp:
        for f in udp.findall("field"):
            name = f.get("name")
            show = f.get("show")
            # SKIP payload fields
            if name and show and name not in EXCLUDED_FIELDS:
                field_name = name.replace("udp.", "")
                pkt[f"udp.{field_name}"] = show
    
    # -------- TCP fields --------
    tcp = root.find(".//proto[@name='tcp']")
    if tcp:
        for f in tcp.findall("field"):
            name = f.get("name")
            show = f.get("show")
            # SKIP payload fields
            if name and show and name not in EXCLUDED_FIELDS:
                field_name = name.replace("tcp.", "")
                pkt[f"tcp.{field_name}"] = show
    
    # -------- Protocol flags (boolean) --------
    for proto in root.findall("proto"):
        pname = proto.get("name")
        if pname in ("ngap", "nas-5gs", "rrc", "s1ap", "x2ap", "http2", "quic", "tls"):
            pkt[f"proto.{pname}"] = True
    
    return pkt
