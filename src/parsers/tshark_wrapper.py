"""tshark_wrapper.py - minimal wrapper to invoke tshark and stream PDML output."""
import subprocess
from typing import Iterator

def run_tshark_pdml(pcap_path: str) -> Iterator[str]:
    cmd = ['tshark', '-r', pcap_path, '-T', 'pdml']
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    assert proc.stdout is not None
    buffer = []
    for line in proc.stdout:
        buffer.append(line)
        if line.strip().endswith('</packet>'):
            yield ''.join(buffer)
            buffer = []
    proc.wait()
