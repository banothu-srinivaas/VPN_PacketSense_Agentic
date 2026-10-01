"""Recommended simple schema constants for Parquet files."""
PACKET_COLUMNS = ['frame_no', 'timestamp', 'src_ip', 'dst_ip', 'protocols', 'msg_type', 'details', 'raw_pdml']
HTTP_COLUMNS = ['frame_no', 'timestamp', 'src_ip', 'dst_ip', 'http_method', 'path', 'status', 'body']
