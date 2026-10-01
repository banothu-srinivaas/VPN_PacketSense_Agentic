#!/usr/bin/env python3
"""Generate synthetic PCAP file with packets from various global locations.\n\nCreates a test .pcap file containing packets between real public IP\naddresses from 8+ geographic regions, plus local private IP ranges.\nUseful for testing the visualization and analytics features without\nperforming an actual live capture.\n\nUsage:\n    python generate_pcap.py\n\nOutput:\n    global_test.pcap in the current directory\n"""

from scapy.all import IP, TCP, UDP, ICMP, wrpcap, Raw
import random
import time

# Real public IP addresses from different regions (Google, Cloudflare, etc.)
GLOBAL_IPS = {
    'USA_East': ['8.8.8.8', '1.1.1.1', '208.67.222.222'],  # Google DNS, Cloudflare, OpenDNS
    'USA_West': ['13.107.42.14', '104.244.42.129'],  # Microsoft, Twitter
    'Europe': ['185.60.216.35', '194.150.168.168'],  # Proton, Spain
    'Asia': ['202.12.27.33', '203.119.101.61'],  # Thailand, Singapore
    'India': ['117.18.232.200', '49.207.53.110'],  # India ISPs
    'Australia': ['1.0.0.1', '58.65.224.41'],  # Cloudflare AU, Telstra
    'Brazil': ['200.221.11.100', '177.72.244.97'],  # Brazil
    'Middle_East': ['37.48.64.137', '195.229.241.222'],  # UAE, Saudi
}

# Your local network IPs
LOCAL_IPS = [
    '192.168.1.100',
    '192.168.1.101', 
    '192.168.1.102',
    '10.0.0.50',
    '10.0.0.51',
]

def generate_packet(src_ip, dst_ip, protocol='tcp', size=None):
    """Generate a single packet"""
    
    # Random ports
    sport = random.randint(1024, 65535)
    dport = random.choice([80, 443, 8080, 53, 22, 3000, 5000])
    
    # Create IP layer
    ip = IP(src=src_ip, dst=dst_ip)
    
    # Create transport layer
    if protocol == 'tcp':
        transport = TCP(sport=sport, dport=dport, flags='S')
    elif protocol == 'udp':
        transport = UDP(sport=sport, dport=dport)
    elif protocol == 'icmp':
        transport = ICMP()
    else:
        transport = TCP(sport=sport, dport=dport)
    
    # Add payload if specified
    if size:
        payload_size = max(0, size - len(ip/transport))
        payload = Raw(load='X' * payload_size)
        return ip/transport/payload
    
    return ip/transport


def generate_flow(src_region, dst_region, packet_count, protocol='tcp'):
    """Generate a flow of packets between two regions"""
    
    # Pick random IPs from regions
    if src_region == 'LOCAL':
        src_ip = random.choice(LOCAL_IPS)
    else:
        src_ip = random.choice(GLOBAL_IPS[src_region])
    
    if dst_region == 'LOCAL':
        dst_ip = random.choice(LOCAL_IPS)
    else:
        dst_ip = random.choice(GLOBAL_IPS[dst_region])
    
    packets = []
    for _ in range(packet_count):
        size = random.choice([64, 128, 512, 1024, 1500, 4096])
        pkt = generate_packet(src_ip, dst_ip, protocol, size)
        packets.append(pkt)
    
    return packets


def main():
    print("🌍 Generating Synthetic PCAP with Global Traffic\n")
    print("="*60)
    
    all_packets = []
    
    # Scenario 1: Local to USA traffic (web browsing)
    print("📡 Generating LOCAL → USA traffic (100 packets)...")
    all_packets.extend(generate_flow('LOCAL', 'USA_East', 100, 'tcp'))
    
    # Scenario 2: India to Asia traffic
    print("📡 Generating India → Asia traffic (50 packets)...")
    all_packets.extend(generate_flow('India', 'Asia', 50, 'tcp'))
    
    # Scenario 3: Europe to USA
    print("📡 Generating Europe → USA traffic (75 packets)...")
    all_packets.extend(generate_flow('Europe', 'USA_West', 75, 'tcp'))
    
    # Scenario 4: Local to Europe (HTTPS)
    print("📡 Generating LOCAL → Europe traffic (60 packets)...")
    all_packets.extend(generate_flow('LOCAL', 'Europe', 60, 'tcp'))
    
    # Scenario 5: Australia to USA
    print("📡 Generating Australia → USA traffic (40 packets)...")
    all_packets.extend(generate_flow('Australia', 'USA_East', 40, 'tcp'))
    
    # Scenario 6: Local to India
    print("📡 Generating LOCAL → India traffic (80 packets)...")
    all_packets.extend(generate_flow('LOCAL', 'India', 80, 'tcp'))
    
    # Scenario 7: Brazil to Europe
    print("📡 Generating Brazil → Europe traffic (30 packets)...")
    all_packets.extend(generate_flow('Brazil', 'Europe', 30, 'tcp'))
    
    # Scenario 8: Middle East to Asia
    print("📡 Generating Middle East → Asia traffic (45 packets)...")
    all_packets.extend(generate_flow('Middle_East', 'Asia', 45, 'tcp'))
    
    # Scenario 9: Local UDP traffic (DNS, streaming)
    print("📡 Generating LOCAL → USA UDP traffic (50 packets)...")
    all_packets.extend(generate_flow('LOCAL', 'USA_East', 50, 'udp'))
    
    # Scenario 10: High-volume flow
    print("📡 Generating HIGH VOLUME LOCAL → USA traffic (200 packets)...")
    all_packets.extend(generate_flow('LOCAL', 'USA_East', 200, 'tcp'))
    
    # Shuffle to make it realistic
    random.shuffle(all_packets)
    
    # Save to PCAP
    output_file = 'global_test.pcap'
    print(f"\n💾 Writing {len(all_packets)} packets to {output_file}...")
    wrpcap(output_file, all_packets)
    
    print("\n" + "="*60)
    print(f"✅ Success! Generated {output_file}")
    print(f"📊 Total packets: {len(all_packets)}")
    print(f"🌍 Regions covered: {len(GLOBAL_IPS)} + LOCAL")
    print("\n📋 Next steps:")
    print(f"   1. Parse: python -m src.cli parse {output_file} data/parquet/global.parquet")
    print(f"   2. Visualize: python app.py data/parquet/global.parquet")
    print("="*60)


if __name__ == '__main__':
    try:
        from scapy.all import IP, TCP, UDP, ICMP, wrpcap, Raw
    except ImportError:
        print("❌ Error: Scapy not installed")
        print("Install with: pip install scapy")
        exit(1)
    
    main()
