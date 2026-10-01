# 5G-PacketSense Integrated

A unified network packet analysis and live capture platform that combines PCAP file analysis with real-time packet monitoring, VPN detection, and geolocation visualization on an interactive world map.

---

## Table of Contents

- [Project Overview](#project-overview)
- [System Requirements](#system-requirements)
- [Software Dependencies](#software-dependencies)
- [Installation](#installation)
- [Steps to Run](#steps-to-run)
- [Project Workflow](#project-workflow)
- [Project Structure](#project-structure)
- [Features](#features)
- [Configuration](#configuration)
- [UI Guide](#ui-guide)
- [CLI Usage](#cli-usage)
- [Troubleshooting](#troubleshooting)
- [Performance Tips](#performance-tips)
- [Security Notes](#security-notes)
- [License](#license)

---

## Project Overview

5G-PacketSense Integrated is a web-based network traffic analysis tool designed for security analysts, network engineers, and researchers. It operates in three modes:

1. **PCAP Analysis Mode** — Upload and analyze captured `.pcap` files with DuckDB SQL queries, geolocation mapping, and protocol statistics.
2. **Live Capture Mode** — Capture packets in real-time from any network interface (requires admin privileges), with instant visualization on a global map.
3. **Switch Monitor Mode** — Monitor all devices on a network switch (requires port mirroring/SPAN), tracking per-device VPN usage with multi-layer detection.

The platform uses a Flask backend with WebSocket streaming, a Scapy-based packet engine, DuckDB for fast SQL analytics, and a single-page frontend powered by Leaflet.js maps, Chart.js, and Socket.IO.

---

## System Requirements

| Requirement        | Details                                                                 |
|--------------------|-------------------------------------------------------------------------|
| **OS**             | Windows 10/11, Linux (Ubuntu 20.04+, Fedora, Arch), macOS 12+         |
| **Python**         | 3.8 or higher (3.10+ recommended)                                      |
| **RAM**            | 4 GB minimum, 8 GB recommended                                         |
| **Disk Space**     | 500 MB for dependencies + space for PCAP/Parquet data files             |
| **Network**        | Internet connection (for GeoIP lookups and VPN database downloads)      |
| **Privileges**     | Administrator (Windows) or root/sudo (Linux/macOS) for live capture     |
| **Packet Library** | Npcap (Windows) or libpcap (Linux/macOS) — required for live capture    |
| **Browser**        | Chrome, Edge, or Firefox (modern version with WebSocket support)        |

### Installing Packet Capture Drivers

- **Windows**: Download and install [Npcap](https://npcap.com/) — check "WinPcap API-compatible mode" during setup.
- **Linux**: Install libpcap — `sudo apt install libpcap-dev` (Debian/Ubuntu) or `sudo dnf install libpcap-devel` (Fedora).
- **macOS**: libpcap is pre-installed. No action needed.

---

## Software Dependencies

All Python dependencies are listed in `requirements.txt`:

| Package              | Purpose                                              |
|----------------------|------------------------------------------------------|
| flask                | Web server framework                                 |
| flask-socketio       | WebSocket support for real-time streaming             |
| flask-cors           | Cross-origin request handling                         |
| scapy                | Packet capture, parsing, and PCAP generation          |
| duckdb               | In-memory SQL analytics on Parquet files              |
| pandas               | Data manipulation for Parquet conversion              |
| pyarrow              | Parquet file I/O with Snappy compression              |
| maxminddb-geolite2   | Offline GeoIP database for IP geolocation             |
| requests             | HTTP client for GeoIP API and VPN database downloads  |
| python-dotenv        | Load environment variables from `.env` file           |
| openai / anthropic   | LLM integration for natural language queries (optional)|
| click                | CLI framework for command-line tools                  |
| tabulate             | Pretty-print query results in terminal                |
| graphviz             | Network topology visualization (optional)             |

---

## Installation

### 1. Clone the repository

```bash
git clone <repository-url>
cd 5G-PacketSense-Integrated
```

### 2. Create a virtual environment

**Windows (PowerShell):**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

**Linux / macOS:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. (Optional) Create environment file for LLM/API keys

```bash
cp .env.example .env
# Edit .env with your API keys if you want AI-powered queries
```

### 5. (Optional) Install Npcap for live capture (Windows only)

Download from https://npcap.com/ and run the installer.

---

## Steps to Run

### Quick Start — Web Interface

```bash
# Start the server
python app.py

# Open in browser
# Navigate to http://localhost:5000
```

The web interface opens with an interactive world map. Use the **Control Panel** on the left to:
- Upload a `.pcap` file for analysis, OR
- Start **Live Capture** to monitor traffic in real-time (requires admin/root)

### Running with Admin Privileges (required for live capture)

**Windows:**
1. Open PowerShell as Administrator
2. Navigate to the project directory
3. Activate the virtual environment and run:
```powershell
.venv\Scripts\Activate.ps1
python app.py
```

**Linux / macOS:**
```bash
source .venv/bin/activate
sudo python app.py
```

### Pre-loading a Parquet file at startup

```bash
python app.py data/parquet/your_file.parquet
```

### Converting a PCAP to Parquet (standalone)

```bash
python pcap_to_parquet_scapy.py data/pcap/capture.pcap data/parquet/capture.parquet
```

### Generating Test Data

```bash
python generate_pcap.py
# Creates global_test.pcap with synthetic packets from 8+ regions
```

---

## Project Workflow

```
┌─────────────────────────────────────────────────────────────────────┐
│                        5G-PacketSense Workflow                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐  │
│  │  PCAP File    │    │ Live Capture │    │ Switch Monitor       │  │
│  │  (.pcap)      │    │ (Scapy sniff)│    │ (Port Mirror/SPAN)   │  │
│  └──────┬───────┘    └──────┬───────┘    └──────────┬───────────┘  │
│         │                   │                       │               │
│         ▼                   ▼                       ▼               │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐  │
│  │ Scapy Parser │    │ Packet       │    │ Per-Device           │  │
│  │ (extract     │    │ Callback     │    │ VPN Detection        │  │
│  │  metadata)   │    │ (real-time)  │    │ (4-layer engine)     │  │
│  └──────┬───────┘    └──────┬───────┘    └──────────┬───────────┘  │
│         │                   │                       │               │
│         ▼                   ▼                       ▼               │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐  │
│  │ Parquet File │    │ WebSocket    │    │ WebSocket            │  │
│  │ (columnar    │    │ Broadcast    │    │ Alerts               │  │
│  │  storage)    │    │ (Socket.IO)  │    │ (Socket.IO)          │  │
│  └──────┬───────┘    └──────┬───────┘    └──────────┬───────────┘  │
│         │                   │                       │               │
│         ▼                   ▼                       ▼               │
│  ┌──────────────┐    ┌──────────────────────────────────────────┐  │
│  │ DuckDB SQL   │    │           Frontend (index.html)          │  │
│  │ Engine       ├───►│  • Leaflet.js Map with flow lines       │  │
│  │ (analytics)  │    │  • Real-time stats dashboard             │  │
│  └──────────────┘    │  • Packet inspector (Wireshark-style)    │  │
│                      │  • VPN detection alerts                  │  │
│                      │  • Protocol & top-talker analytics       │  │
│                      └──────────────────────────────────────────┘  │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│  VPN Detection Engine (4 layers):                                   │
│  1. ISP/Org keyword matching (40+ providers)                        │
│  2. Known VPN ASN database (30+ ASNs)                               │
│  3. X4BNet/Tor public IP range lists (auto-downloaded daily)        │
│  4. vpnapi.io public API (1000 free queries/day)                    │
├─────────────────────────────────────────────────────────────────────┤
│  GeoIP Resolution:                                                  │
│  1. MaxMind GeoLite2 local database (offline, fast)                 │
│  2. ip-api.com REST API fallback (online, rate-limited)             │
└─────────────────────────────────────────────────────────────────────┘
```

### Data Flow Summary

1. **Input**: PCAP file upload, live packet capture, or switch mirror port
2. **Parse**: Scapy extracts packet headers (IP, TCP/UDP, ports, flags, size)
3. **Enrich**: GeoIP lookup adds lat/lon/city/country; VPN detection adds provider info
4. **Store**: Packets saved as Parquet (columnar format) for fast SQL queries
5. **Analyze**: DuckDB runs SQL aggregation (flows, stats, top talkers, port distribution)
6. **Visualize**: Frontend renders flows on a Leaflet.js world map with animated lines
7. **Stream**: Live packets broadcast via WebSocket for real-time map updates

---

## Project Structure

```
5G-PacketSense-Integrated/
├── app.py                          # Main Flask server (REST API + WebSocket + capture engine)
├── requirements.txt                # Python package dependencies
├── .env.example                    # Template for environment variables (API keys)
├── pcap_to_parquet_scapy.py        # Standalone PCAP → Parquet converter
├── generate_pcap.py                # Synthetic test PCAP generator
├── debug_flows.py                  # Debugging utility for flow data
│
├── static/
│   └── index.html                  # Single-page frontend (HTML + CSS + JavaScript)
│
├── src/
│   ├── cli.py                      # CLI tool (parse, query, schema, interactive)
│   ├── config.py                   # Environment configuration loader
│   │
│   ├── agents/
│   │   └── llm_client.py           # Multi-provider LLM client (Anthropic, OpenAI, Gemini, Ollama)
│   │
│   ├── parsers/
│   │   ├── scapy_parser.py         # PCAP → structured dict parser (no tshark needed)
│   │   ├── pdml_parser.py          # PDML XML parser (tshark pipeline)
│   │   ├── tshark_wrapper.py       # tshark subprocess wrapper
│   │   ├── field_extractors.py     # Packet field extraction helpers
│   │   └── http_json_extractor.py  # HTTP payload JSON extractor
│   │
│   ├── query/
│   │   ├── duckdb_loader.py        # DuckDB connection and Parquet loader
│   │   ├── sql_executor.py         # SQL query execution engine
│   │   └── formatters.py           # Query result formatters
│   │
│   ├── transformers/
│   │   ├── json_to_parquet.py      # JSON/dict → Parquet converter
│   │   └── parquet_schema.py       # Parquet column schema definitions
│   │
│   ├── tools/
│   │   ├── callflow_generator.py   # Network call-flow DOT generator
│   │   └── dot_to_png.py           # Graphviz DOT → PNG converter
│   │
│   └── utils/
│       └── logger.py               # Logging configuration
│
├── data/
│   ├── pcap/                       # Captured / uploaded PCAP files
│   ├── parquet/                    # Converted Parquet files (for DuckDB)
│   └── vpn_lists/                  # Auto-downloaded VPN IP databases
│       ├── x4bnet_ipv4.txt         # X4BNet VPN IP ranges (updated daily)
│       └── tor_exit_nodes.txt      # Tor exit node IP list
│
└── examples/
    ├── sample_callflow.dot         # Example network call-flow graph
    └── sample_query.txt            # Example natural language queries
```

---

## Features

### Dual Mode Operation

| Mode | Description |
|------|-------------|
| **PCAP Analysis** | Upload `.pcap` files → auto-convert to Parquet → SQL analytics, geo-mapping, protocol stats |
| **Live Capture** | Real-time Scapy capture → WebSocket streaming → animated map, live stats, auto-save to PCAP |

### Switch Monitor (Enterprise VPN Detection)

- Monitors all traffic on a network switch (requires port mirroring / SPAN)
- Tracks every device on the monitored subnet
- Detects VPN usage per-device using 4-layer detection engine
- Real-time alerts via WebSocket when VPN connections are detected
- Dashboard with device count, VPN users, alert log, and map overlay

### VPN Detection (4 Layers)

1. **Keyword Matching** — 40+ VPN providers identified by ISP/org name patterns
2. **ASN Database** — 30+ known VPN-associated Autonomous System Numbers
3. **IP Range Matching** — X4BNet public VPN IP lists + Tor exit nodes (auto-downloaded)
4. **API Verification** — vpnapi.io public API (1000 free queries/day)

### Analytics & Visualization

- **Interactive World Map** — Leaflet.js with animated flow lines between cities
- **Wireshark-Style Inspector** — Layer-by-layer packet dissection
- **Real-Time Dashboard** — Packets/sec, bandwidth, top talkers, protocol distribution
- **SQL-Powered Queries** — DuckDB for fast aggregation on millions of packets
- **AI Queries** — Natural language to SQL translation via LLM (optional)

---

## Configuration

### Environment Variables

Copy `.env.example` to `.env` and set values as needed:

| Variable | Description | Default |
|----------|-------------|---------|
| `LLM_PROVIDER` | LLM backend: `ollama`, `openai`, `anthropic`, `openrouter`, `gemini` | `ollama` |
| `OLLAMA_URL` | Ollama server URL | `http://localhost:11434/v1` |
| `OLLAMA_MODEL` | Ollama model name | `llama3.2` |
| `OPENAI_API_KEY` | OpenAI API key | — |
| `ANTHROPIC_API_KEY` | Anthropic Claude API key | — |
| `OPENROUTER_API_KEY` | OpenRouter API key | — |
| `GEMINI_API_KEY` | Google Gemini API key | — |
| `VPNAPI_IO_KEY` | vpnapi.io API key (optional, 1000 free/day) | — |

### Dependency Files

The application automatically downloads and caches these files in `data/vpn_lists/`:

| File | Source | Purpose |
|------|--------|---------|
| `x4bnet_ipv4.txt` | X4BNet GitHub | Known VPN IP CIDR ranges (updated daily) |
| `tor_exit_nodes.txt` | dan.me.uk | Tor exit node IP addresses |

PCAP files captured or uploaded are stored in `data/pcap/`, and their converted Parquet counterparts in `data/parquet/`.

---

## UI Guide

### Top Bar
- **Brand logo** and mode indicator (Idle / Live Capture / PCAP Analysis)
- **Switch Monitor** button — opens the VPN monitoring panel
- **Control Panel** button — toggles the configuration sidebar

### Control Panel (Left)
- **Live Capture / Load PCAP** buttons — choose data source
- **Protocol Filter** — filter by TCP, UDP, or all
- **Flow Limit** — control number of displayed flows (10–1000)
- **Min Packets** — hide flows below a packet threshold
- **Active Flows** — clickable list to zoom to specific flows on the map
- **Recent Packets** — real-time packet table (click to inspect)

### Analytics Panel (Right)
- **Key Metrics** — total packets, unique IPs, total data, avg packet size
- **Duration & Rate** — capture duration and packets/second
- **VPN Detections** — flagged VPN IPs with provider and detection method
- **Top Talkers** — IPs generating the most traffic by volume
- **Top Ports** — most active destination ports
- **Protocol Distribution** — TCP/UDP/other breakdown

### Switch Monitor Panel
- **Configuration** — select interface and subnet (CIDR)
- **Start/Stop** — begin/end switch monitoring
- **Stats** — device count, VPN users, alerts, total packets
- **Devices Tab** — all devices with VPN status and traffic details
- **VPN Alerts Tab** — chronological list of VPN detection events

---

## CLI Usage

```bash
# Parse PCAP to Parquet (via tshark)
python -m src.cli parse input.pcap output.parquet

# Query with natural language (requires LLM API key)
python -m src.cli query data.parquet "show all TCP packets from 192.168.1.1"

# Query with raw SQL
python -m src.cli query data.parquet "SELECT * FROM packets LIMIT 10" --no-llm

# Show Parquet schema
python -m src.cli schema data.parquet

# Interactive mode
python -m src.cli interactive capture.pcap --provider ollama
```

---

## Troubleshooting

### "Permission denied" when starting live capture
- **Windows**: Right-click PowerShell → "Run as Administrator"
- **Linux/macOS**: Use `sudo python app.py`

### "No module named 'scapy'" or other import errors
```bash
pip install -r requirements.txt
```

### WebSocket connection fails / No live packets
- Check firewall allows port 5000
- Try `http://localhost:5000` instead of `127.0.0.1:5000`
- Check browser console for WebSocket errors

### PCAP upload shows no packets
- Verify the file is valid `.pcap` or `.pcapng`
- Check server console for error messages
- Very large files (>100 MB) may take time to process

### Map shows no flows
- Packets need valid public IP addresses for geolocation
- Private IPs (10.x, 192.168.x) are mapped to your public location
- Unknown locations are skipped (see "Unknown Locs" in Analytics)

### GeoIP warnings at startup
```bash
pip install maxminddb-geolite2
```
Without this package, the app falls back to the ip-api.com online API (rate-limited).

### Live capture not working on Linux
```bash
sudo apt install libpcap-dev   # Debian/Ubuntu
sudo dnf install libpcap-devel  # Fedora
```

---

## Performance Tips

- **Live Capture**: History capped at 1000 packets; map paths limited for smooth rendering
- **Large PCAPs**: Files >100 MB may take a minute to process; use filters to reduce map clutter
- **Flow Limit**: Reduce to 50–100 if the map becomes sluggish
- **Browser**: Chrome/Edge recommended for best WebSocket performance
- **DuckDB**: SQL queries remain fast even on datasets with millions of rows

---

## Security Notes

1. **Privilege Requirements** — Live capture needs raw socket access (admin/root)
2. **Network Sensitivity** — Packet captures may contain credentials and personal data
3. **Port Exposure** — The app binds to `0.0.0.0:5000` — restrict access on shared networks
4. **API Keys** — Store in `.env` file (not in code); never commit `.env` to version control
5. **VPN Lists** — Downloaded from public GitHub repos and verified sources only

---

## License

See LICENSE file for details.

---

**Built for network engineers, security analysts, and researchers who need to understand network traffic visually and interactively.**
