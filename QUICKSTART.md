# 5G-PacketSense Integrated - Quick Start Guide

## 🚀 3-Minute Setup

### Step 1: Install Dependencies

```bash
# Create virtual environment
python -m venv venv

# Activate it
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Choose Your Mode

#### Option A: Live Capture (Real-time monitoring)

```bash
# Run as Administrator (Windows) or with sudo (Linux/Mac)
python app.py
```

1. Open http://localhost:5000
2. Click **"Live Capture"** button
3. Watch packets appear in real-time on the map
4. Click **"Stop & Save Capture"** when done

#### Option B: PCAP Analysis (Analyze existing capture)

```bash
# Just start the server
python app.py
```

1. Open http://localhost:5000
2. Click **"Load PCAP"** button
3. Select your `.pcap` or `.pcapng` file
4. Data loads automatically on the map!

### Step 3: Explore Features

- **Map**: Click on packet flow lines to see details
- **Control Panel**: Filter by protocol, adjust flow limits
- **Analytics Window**: View statistics, top talkers, protocols
- **Recent Packets**: Click any packet to see Wireshark-style details
- **Reset All**: Clear everything and start fresh

## � Example Workflows

### Workflow 1: Network Troubleshooting

1. Start server: `python app.py`
2. Click **"Live Capture"**
3. Reproduce the network issue
4. Watch traffic patterns on the map in real-time
5. Click **"Stop & Save"**
6. Upload the saved PCAP to analyze with filters

### Workflow 2: Security Analysis

1. Get a suspicious PCAP file
2. Start server: `python app.py`
3. Click **"Load PCAP"** and select file
4. Use Protocol Filter to focus on specific traffic
5. Click flow lines to inspect individual packets
6. Check Analytics for unusual patterns (unknown locations, rare ports)

### Workflow 3: Protocol Analysis

1. Capture traffic with your application running
2. Load the PCAP file
3. Filter by specific protocol (TCP/UDP)
4. View geographic distribution on map
5. Inspect packet details in Wireshark-style viewer
6. Export data using DuckDB queries if needed

## 🆘 Common Issues

**Q: "Permission denied" error when starting live capture?**  
A: Run as Administrator (Windows) or use `sudo python app.py` (Linux/Mac). Live capture requires raw socket access.

**Q: No packets showing on the map?**  
A: Check that:

- Firewall allows the application
- Network interface is accessible
- Geolocation data is available (see "Unknown Locs" in Analytics)
- You clicked "Apply Filters" after loading PCAP

**Q: PCAP upload fails?**  
A: Ensure:

- File is valid `.pcap` or `.pcapng` format
- File size is reasonable (<500MB recommended)
- You have write permissions to `data/` directory

**Q: WebSocket disconnects in live capture?**  
A: Check browser console for errors. Try:

- Different browser (Chrome/Edge recommended)
- Disabling browser extensions
- Checking firewall/antivirus settings

## 🎯 Tips & Tricks

1. **Performance**: Reduce flow limit (10-50) for better map performance with large captures
2. **Filtering**: Use Min Packets filter to remove low-volume flows
3. **Details**: Click packets in Recent Packets table for full layer-by-layer analysis
4. **Save Work**: Live captures auto-save to `data/pcap/` when stopped
5. **Quick Reset**: Use "Reset All" button to clear map and start fresh

## 📚 Learn More

- **Full Documentation**: See `README.md` for detailed features
- **Project Structure**: Check `README.md` for code organization
- **Advanced Usage**: See README for custom queries and extensions

---

**Ready to analyze your network! 🔍📡**
