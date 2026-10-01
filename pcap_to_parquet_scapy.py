"""Standalone PCAP to Parquet converter using Scapy.\n\nConverts raw .pcap files into columnar Parquet format for fast\nSQL-based analysis with DuckDB. Uses tshark-compatible column names\n(e.g. 'frame.frame.number', 'ip.ip.src') so the output can be loaded\nby both the original tshark-based pipeline and this integrated app.\n\nUsage:\n    python pcap_to_parquet_scapy.py <input_pcap> <output_parquet>\n\nExample:\n    python pcap_to_parquet_scapy.py data/pcap/capture.pcap data/parquet/capture.parquet\n"""\n\nimport pandas as pd\nfrom scapy.all import rdpcap, IP, TCP, UDP, Ether\nimport sys\nimport os

def pcap_to_parquet(pcap_file, parquet_file):
    print(f"Reading {pcap_file}...")
    try:
        packets = rdpcap(pcap_file)
    except Exception as e:
        print(f"Error reading PCAP: {e}")
        return

    data = []
    print(f"Processing {len(packets)} packets...")
    
    for i, pkt in enumerate(packets):
        # Basic frame info
        row = {
            'frame.frame.number': i + 1,
            'frame.frame.time': float(pkt.time),
            'frame.frame.len': len(pkt),
            'frame.frame.protocols': 'eth', 
            'ip.ip.src': None,
            'ip.ip.dst': None
        }
        
        # Build protocol string and extract IP
        if IP in pkt:
            row['frame.frame.protocols'] += ':ip'
            row['ip.ip.src'] = pkt[IP].src
            row['ip.ip.dst'] = pkt[IP].dst
            
            proto = pkt[IP].proto
            if proto == 6: # TCP
                row['frame.frame.protocols'] += ':tcp'
            elif proto == 17: # UDP
                row['frame.frame.protocols'] += ':udp'
            elif proto == 1: # ICMP
                row['frame.frame.protocols'] += ':icmp'
        
        data.append(row)
        
    df = pd.DataFrame(data)
    
    # Filter only IP packets as app.py requires src/dst ip
    # But keep non-IP if you want to see them (app.py filters them in SQL anyway)
    # The app.py query: WHERE "ip.ip.src" IS NOT NULL AND "ip.ip.dst" IS NOT NULL
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(parquet_file), exist_ok=True)
    
    print(f"Writing {len(df)} packets to {parquet_file}...")
    df.to_parquet(parquet_file)
    print("Done.")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python pcap_to_parquet_scapy.py <input_pcap> <output_parquet>")
        sys.exit(1)
        
    pcap_to_parquet(sys.argv[1], sys.argv[2])
