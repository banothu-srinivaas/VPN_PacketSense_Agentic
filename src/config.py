"""Configuration for 5G-PacketSense"""
import os
from dotenv import load_dotenv
load_dotenv()

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
DATA_DIR = os.getenv('TALK_TO_PCAP_DATA_DIR', './data')
LOG_LEVEL = os.getenv('TALK_TO_PCAP_LOG_LEVEL', 'INFO')
AUTHOR = 'Syamala Jayanthi'
