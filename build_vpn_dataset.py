#!/usr/bin/env python3
"""Build a VPN IP intelligence dataset from sources used by this project.

This script pulls VPN IP data from the same public lists used in app.py,
enriches each IP with both local (MaxMind) and online (ip-api) geodata,
compares both data sources with a quality score, and writes a CSV dataset.

Example:
    python build_vpn_dataset.py --max-ips 2000 --output data/vpn_lists/vpn_dataset.csv

Notes:
    - This script now writes three datasets by default:
      * Combined local-vs-online comparison CSV (--output)
      * Local-only GeoLite2 CSV (--local-output)
      * Online-only ip-api CSV (--online-output)
    - Online lookups use ip-api batch endpoint and may be rate-limited.
    - Local enrichment can use GeoLite2-City.mmdb and GeoLite2-ASN.mmdb if present.
    - If local DBs are unavailable, the script still runs with online data only.
"""

from __future__ import annotations

import argparse
import ast
import csv
import ipaddress
import importlib
import math
import time
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import requests

try:
    import geoip2.database
except Exception:
    geoip2 = None

try:
    _mmdb_mod = importlib.import_module("maxminddb_geolite2")
    open_geolite2_database = getattr(_mmdb_mod, "open_database", None)
except Exception:
    open_geolite2_database = None


DEFAULT_SOURCES = {
    "x4bnet_ipv4": "https://raw.githubusercontent.com/X4BNet/lists_vpn/main/output/vpn/ipv4.txt",
    "tor_exit_nodes": "https://www.dan.me.uk/torlist/?exit",
}

IP_API_BATCH_URL = (
    "http://ip-api.com/batch"
    "?fields=status,message,country,city,lat,lon,isp,org,as,asname,mobile,proxy,hosting,query"
)


DEFAULT_VPN_PROVIDERS = {
    "NordVPN": ["nordvpn", "nord vpn", "tesonet", "tefincom"],
    "ExpressVPN": ["expressvpn", "express vpn", "express networks"],
    "ProtonVPN": ["protonvpn", "proton vpn", "proton ag", "proton technologies"],
    "Surfshark": ["surfshark"],
    "Private Internet Access": ["private internet access", "london trust media"],
    "Mullvad": ["mullvad", "31173 services"],
    "Windscribe": ["windscribe"],
    "TorGuard": ["torguard"],
    "PureVPN": ["purevpn", "gaditek"],
}

DEFAULT_VPN_ASN_DATABASE = {
    "AS212238": "NordVPN",
    "AS18450": "ExpressVPN",
    "AS209103": "ProtonVPN",
    "AS51852": "ProtonVPN",
    "AS198093": "Mullvad",
    "AS31173": "Mullvad",
    "AS25379": "Windscribe",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build VPN IP intelligence dataset CSV"
    )
    parser.add_argument(
        "--output",
        default="data/vpn_lists/vpn_ip_dataset.csv",
        help="Output CSV path",
    )
    parser.add_argument(
        "--local-output",
        default="data/vpn_lists/vpn_ip_dataset_local.csv",
        help="Output CSV path for local GeoLite2-only enrichment",
    )
    parser.add_argument(
        "--online-output",
        default="data/vpn_lists/vpn_ip_dataset_online.csv",
        help="Output CSV path for online ip-api-only enrichment",
    )
    parser.add_argument(
        "--cache-dir",
        default="data/vpn_lists",
        help="Directory to cache downloaded source lists",
    )
    parser.add_argument(
        "--cache-max-age-hours",
        type=int,
        default=24,
        help="Reuse cached source files newer than this age",
    )
    parser.add_argument(
        "--samples-per-cidr",
        type=int,
        default=1,
        help="How many representative IPs to sample per CIDR entry",
    )
    parser.add_argument(
        "--max-ips",
        type=int,
        default=2000,
        help="Maximum number of IPs to enrich (0 means no limit)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Batch size for ip-api lookups (max 100)",
    )
    parser.add_argument(
        "--request-timeout",
        type=int,
        default=15,
        help="HTTP timeout in seconds",
    )
    parser.add_argument(
        "--force-refresh",
        action="store_true",
        help="Ignore source cache and always re-download",
    )
    parser.add_argument(
        "--city-db-path",
        default="",
        help="Optional path to GeoLite2-City.mmdb",
    )
    parser.add_argument(
        "--asn-db-path",
        default="",
        help="Optional path to GeoLite2-ASN.mmdb",
    )
    parser.add_argument(
        "--app-path",
        default="app.py",
        help="Path to app.py so VPN provider dictionaries can be reused",
    )
    return parser.parse_args()


def chunked(items: List[str], size: int) -> Iterable[List[str]]:
    for idx in range(0, len(items), size):
        yield items[idx : idx + size]


def download_with_cache(
    name: str,
    url: str,
    cache_dir: Path,
    max_age_hours: int,
    force_refresh: bool,
    timeout: int,
) -> str:
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / f"{name}.txt"
    max_age_seconds = max_age_hours * 3600

    if cache_path.exists() and not force_refresh:
        file_age = time.time() - cache_path.stat().st_mtime
        if file_age < max_age_seconds:
            print(f"[CACHE] Using cached {name} (age={int(file_age / 3600)}h)")
            return cache_path.read_text(encoding="utf-8", errors="ignore")

    print(f"[DOWNLOAD] Fetching {name} from {url}")
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    cache_path.write_text(response.text, encoding="utf-8")
    return response.text


def sample_ips_from_network(
    network: ipaddress.IPv4Network, max_samples: int
) -> List[str]:
    if network.num_addresses == 1:
        return [str(network.network_address)]

    if network.num_addresses == 2:
        candidates = [network.network_address, network.broadcast_address]
    else:
        candidates = [
            ipaddress.IPv4Address(int(network.network_address) + 1),
            ipaddress.IPv4Address(
                int(network.network_address) + (network.num_addresses // 2)
            ),
            ipaddress.IPv4Address(int(network.broadcast_address) - 1),
        ]

    unique = []
    seen = set()
    for ip in candidates:
        if ip not in seen:
            seen.add(ip)
            unique.append(str(ip))

    if max_samples <= 0:
        return unique
    return unique[:max_samples]


def collect_candidate_ips(
    source_text_by_name: Dict[str, str], samples_per_cidr: int
) -> Tuple[List[str], Dict[str, Dict[str, object]]]:
    ordered_ips: List[str] = []
    meta: Dict[str, Dict[str, object]] = {}

    for source_name, text in source_text_by_name.items():
        lines = text.splitlines()
        for raw_line in lines:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue

            token = line.split()[0]

            try:
                network = ipaddress.ip_network(token, strict=False)
            except ValueError:
                continue

            if network.version != 4:
                continue

            if isinstance(network, ipaddress.IPv4Network) and network.prefixlen == 32:
                sampled_ips = [str(network.network_address)]
            else:
                sampled_ips = sample_ips_from_network(network, samples_per_cidr)

            for ip in sampled_ips:
                if ip not in meta:
                    meta[ip] = {
                        "sources": set(),
                        "raw_entries": set(),
                        "from_cidr": False,
                    }
                    ordered_ips.append(ip)

                meta[ip]["sources"].add(source_name)
                meta[ip]["raw_entries"].add(token)
                if "/" in token and not token.endswith("/32"):
                    meta[ip]["from_cidr"] = True

    return ordered_ips, meta


def find_first_existing_path(candidates: List[Path]) -> Optional[Path]:
    for path in candidates:
        if path.exists() and path.is_file():
            return path
    return None


def init_local_readers(args: argparse.Namespace) -> Dict[str, object]:
    readers: Dict[str, object] = {
        "city": None,
        "asn": None,
        "geolite2": None,
    }

    city_candidates = [
        Path(args.city_db_path) if args.city_db_path else None,
        Path("data/GeoLite2-City.mmdb"),
        Path("GeoLite2-City.mmdb"),
        Path("data/vpn_lists/GeoLite2-City.mmdb"),
    ]
    asn_candidates = [
        Path(args.asn_db_path) if args.asn_db_path else None,
        Path("data/GeoLite2-ASN.mmdb"),
        Path("GeoLite2-ASN.mmdb"),
        Path("data/vpn_lists/GeoLite2-ASN.mmdb"),
    ]

    city_candidates = [p for p in city_candidates if p is not None]
    asn_candidates = [p for p in asn_candidates if p is not None]

    city_db_path = find_first_existing_path(city_candidates)
    asn_db_path = find_first_existing_path(asn_candidates)

    if geoip2 is not None and city_db_path is not None:
        readers["city"] = geoip2.database.Reader(str(city_db_path))
        print(f"[LOCAL-DB] Loaded city DB: {city_db_path}")

    if geoip2 is not None and asn_db_path is not None:
        readers["asn"] = geoip2.database.Reader(str(asn_db_path))
        print(f"[LOCAL-DB] Loaded ASN DB: {asn_db_path}")

    if readers["city"] is None and open_geolite2_database is not None:
        try:
            readers["geolite2"] = open_geolite2_database()
            print("[LOCAL-DB] Loaded maxminddb-geolite2 bundled city DB")
        except Exception as exc:
            print(f"[LOCAL-DB] Failed to load maxminddb-geolite2 DB: {exc}")

    if readers["city"] is None and readers["geolite2"] is None:
        print("[LOCAL-DB] No local city DB available, local geolocation will be empty")

    return readers


def close_local_readers(readers: Dict[str, object]) -> None:
    for key in ["city", "asn", "geolite2"]:
        reader = readers.get(key)
        if reader is not None:
            try:
                reader.close()
            except Exception:
                pass


def lookup_local(ip: str, readers: Dict[str, object]) -> Dict[str, object]:
    out = {
        "country": "",
        "city": "",
        "lat": None,
        "lon": None,
        "isp": "",
        "asn": "",
        "as_org": "",
    }

    if readers.get("city") is not None:
        try:
            city_resp = readers["city"].city(ip)
            out["country"] = city_resp.country.name or ""
            out["city"] = city_resp.city.name or ""
            out["lat"] = city_resp.location.latitude
            out["lon"] = city_resp.location.longitude
        except Exception:
            pass
    elif readers.get("geolite2") is not None:
        try:
            data = readers["geolite2"].get(ip) or {}
            out["country"] = (
                data.get("country", {}).get("names", {}).get("en", "")
                if isinstance(data, dict)
                else ""
            )
            out["city"] = (
                data.get("city", {}).get("names", {}).get("en", "")
                if isinstance(data, dict)
                else ""
            )
            out["lat"] = (
                data.get("location", {}).get("latitude")
                if isinstance(data, dict)
                else None
            )
            out["lon"] = (
                data.get("location", {}).get("longitude")
                if isinstance(data, dict)
                else None
            )
        except Exception:
            pass

    if readers.get("asn") is not None:
        try:
            asn_resp = readers["asn"].asn(ip)
            asn_no = asn_resp.autonomous_system_number
            if asn_no:
                out["asn"] = f"AS{asn_no}"
            out["as_org"] = asn_resp.autonomous_system_organization or ""
        except Exception:
            pass

    return out


def parse_asn_string(value: str) -> Tuple[str, str]:
    if not value:
        return "", ""
    parts = value.strip().split(maxsplit=1)
    if not parts:
        return "", ""
    asn = parts[0] if parts[0].upper().startswith("AS") else ""
    org = parts[1] if len(parts) > 1 else ""
    return asn, org


def failed_online_record(message: str) -> Dict[str, object]:
    return {
        "status": "fail",
        "message": message,
        "country": "",
        "city": "",
        "lat": None,
        "lon": None,
        "isp": "",
        "asn": "",
        "as_org": "",
        "proxy": False,
        "hosting": False,
        "mobile": False,
    }


def lookup_online_batch(
    ips: List[str], batch_size: int, timeout: int
) -> Dict[str, Dict[str, object]]:
    result: Dict[str, Dict[str, object]] = {}
    session = requests.Session()

    safe_batch_size = max(1, min(batch_size, 100))

    for chunk in chunked(ips, safe_batch_size):
        payload = [{"query": ip} for ip in chunk]
        try:
            response = session.post(IP_API_BATCH_URL, json=payload, timeout=timeout)
            response.raise_for_status()
            rows = response.json()
        except Exception as exc:
            print(f"[ONLINE] Batch lookup failed for {len(chunk)} IPs: {exc}")
            for ip in chunk:
                result[ip] = failed_online_record(str(exc))
            continue

        for row in rows:
            ip = str(row.get("query", "")).strip()
            if not ip:
                continue

            asn, as_org_from_as = parse_asn_string(str(row.get("as", "")))
            as_name = str(row.get("asname", "") or "").strip()
            as_org = as_name or as_org_from_as or str(row.get("org", "") or "").strip()

            result[ip] = {
                "status": str(row.get("status", "")),
                "message": str(row.get("message", "")),
                "country": str(row.get("country", "") or ""),
                "city": str(row.get("city", "") or ""),
                "lat": row.get("lat"),
                "lon": row.get("lon"),
                "isp": str(row.get("isp", "") or ""),
                "asn": asn,
                "as_org": as_org,
                "proxy": bool(row.get("proxy", False)),
                "hosting": bool(row.get("hosting", False)),
                "mobile": bool(row.get("mobile", False)),
            }

        remaining = response.headers.get("X-Rl")
        reset_sec = response.headers.get("X-Ttl")
        if remaining is not None and reset_sec is not None:
            try:
                if int(remaining) <= 0 and int(reset_sec) > 0:
                    wait_for = int(reset_sec) + 1
                    print(f"[ONLINE] Rate limit reached, waiting {wait_for}s")
                    time.sleep(wait_for)
            except ValueError:
                pass

    session.close()
    return result


def quality_score(record: Dict[str, object]) -> int:
    score = 0
    if str(record.get("country", "")).strip():
        score += 2
    if str(record.get("city", "")).strip():
        score += 1
    if record.get("lat") is not None and record.get("lon") is not None:
        score += 2
    if str(record.get("isp", "")).strip():
        score += 2
    if str(record.get("asn", "")).strip():
        score += 2
    if str(record.get("as_org", "")).strip():
        score += 1
    return score


def build_local_geolite2_records(
    ips: List[str], readers: Dict[str, object]
) -> Dict[str, Dict[str, object]]:
    """Local enrichment function using GeoLite2/local MaxMind DB readers."""
    return {ip: lookup_local(ip, readers) for ip in ips}


def build_online_ip_api_records(
    ips: List[str], batch_size: int, timeout: int
) -> Dict[str, Dict[str, object]]:
    """Online enrichment function using ip-api batch endpoint."""
    return lookup_online_batch(ips, batch_size, timeout)


LOCAL_CSV_FIELDNAMES = [
    "ip",
    "sources",
    "raw_entries",
    "from_cidr",
    "country",
    "city",
    "latitude",
    "longitude",
    "isp",
    "asn",
    "as_org",
    "quality_score",
]

ONLINE_CSV_FIELDNAMES = [
    "ip",
    "sources",
    "raw_entries",
    "from_cidr",
    "status",
    "message",
    "country",
    "city",
    "latitude",
    "longitude",
    "isp",
    "asn",
    "as_org",
    "proxy",
    "hosting",
    "mobile",
    "quality_score",
]


def build_local_csv_rows(
    ips: List[str],
    ip_meta: Dict[str, Dict[str, object]],
    local_data: Dict[str, Dict[str, object]],
) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    for ip in ips:
        local = local_data.get(ip, {})
        meta = ip_meta[ip]
        rows.append(
            {
                "ip": ip,
                "sources": "|".join(sorted(meta["sources"])),
                "raw_entries": "|".join(sorted(meta["raw_entries"])),
                "from_cidr": bool(meta["from_cidr"]),
                "country": local.get("country", ""),
                "city": local.get("city", ""),
                "latitude": local.get("lat"),
                "longitude": local.get("lon"),
                "isp": local.get("isp", ""),
                "asn": local.get("asn", ""),
                "as_org": local.get("as_org", ""),
                "quality_score": quality_score(local),
            }
        )
    return rows


def build_online_csv_rows(
    ips: List[str],
    ip_meta: Dict[str, Dict[str, object]],
    online_data: Dict[str, Dict[str, object]],
) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    for ip in ips:
        online = online_data.get(ip, failed_online_record("missing_online_result"))
        meta = ip_meta[ip]
        rows.append(
            {
                "ip": ip,
                "sources": "|".join(sorted(meta["sources"])),
                "raw_entries": "|".join(sorted(meta["raw_entries"])),
                "from_cidr": bool(meta["from_cidr"]),
                "status": online.get("status", ""),
                "message": online.get("message", ""),
                "country": online.get("country", ""),
                "city": online.get("city", ""),
                "latitude": online.get("lat"),
                "longitude": online.get("lon"),
                "isp": online.get("isp", ""),
                "asn": online.get("asn", ""),
                "as_org": online.get("as_org", ""),
                "proxy": bool(online.get("proxy", False)),
                "hosting": bool(online.get("hosting", False)),
                "mobile": bool(online.get("mobile", False)),
                "quality_score": quality_score(online),
            }
        )
    return rows


def write_rows_csv(
    output_path: Path, fieldnames: List[str], rows: List[Dict[str, object]]
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return r * c


def compare_local_vs_online(
    local: Dict[str, object], online: Dict[str, object]
) -> Tuple[str, Dict[str, object], int, int, str]:
    local_score = quality_score(local)
    online_score = quality_score(online)

    if online_score > local_score:
        chosen_source = "online"
        chosen = online
    elif local_score > online_score:
        chosen_source = "local"
        chosen = local
    else:
        # Tie-breaker: prefer online when it has proxy/hosting signals.
        if bool(online.get("proxy")) or bool(online.get("hosting")):
            chosen_source = "online"
            chosen = online
        else:
            chosen_source = "local"
            chosen = local

    notes: List[str] = []
    local_country = str(local.get("country", "")).strip()
    online_country = str(online.get("country", "")).strip()
    if (
        local_country
        and online_country
        and local_country.lower() != online_country.lower()
    ):
        notes.append("country_mismatch")

    if (
        local.get("lat") is not None
        and local.get("lon") is not None
        and online.get("lat") is not None
        and online.get("lon") is not None
    ):
        try:
            dist = haversine_km(
                float(local["lat"]),
                float(local["lon"]),
                float(online["lat"]),
                float(online["lon"]),
            )
            if dist > 300:
                notes.append(f"geo_distance_km>{int(dist)}")
        except Exception:
            pass

    return chosen_source, chosen, local_score, online_score, ";".join(notes)


def load_provider_data_from_app(
    app_path: Path,
) -> Tuple[Dict[str, List[str]], Dict[str, str]]:
    if not app_path.exists():
        print(f"[PROVIDERS] app.py not found at {app_path}, using defaults")
        return DEFAULT_VPN_PROVIDERS, DEFAULT_VPN_ASN_DATABASE

    try:
        src = app_path.read_text(encoding="utf-8", errors="ignore")
        tree = ast.parse(src)
    except Exception as exc:
        print(f"[PROVIDERS] Failed to parse {app_path}: {exc}, using defaults")
        return DEFAULT_VPN_PROVIDERS, DEFAULT_VPN_ASN_DATABASE

    providers = None
    asn_db = None

    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "VPN_PROVIDERS":
                try:
                    providers = ast.literal_eval(node.value)
                except Exception:
                    providers = None
            if isinstance(target, ast.Name) and target.id == "VPN_ASN_DATABASE":
                try:
                    asn_db = ast.literal_eval(node.value)
                except Exception:
                    asn_db = None

    if not isinstance(providers, dict):
        providers = DEFAULT_VPN_PROVIDERS
    if not isinstance(asn_db, dict):
        asn_db = DEFAULT_VPN_ASN_DATABASE

    print(
        f"[PROVIDERS] Loaded {len(providers)} provider keyword groups and {len(asn_db)} ASN mappings"
    )
    return providers, asn_db


def detect_provider(
    sources: List[str],
    chosen: Dict[str, object],
    online: Dict[str, object],
    providers: Dict[str, List[str]],
    asn_db: Dict[str, str],
) -> Tuple[str, str]:
    if "tor_exit_nodes" in sources:
        return "Tor Network", "source_tor"

    asn_candidate = str(chosen.get("asn", "") or online.get("asn", "")).strip()
    if asn_candidate in asn_db:
        return asn_db[asn_candidate], "asn_database"

    text = " ".join(
        [
            str(chosen.get("isp", "") or ""),
            str(chosen.get("as_org", "") or ""),
            str(online.get("isp", "") or ""),
            str(online.get("as_org", "") or ""),
        ]
    ).lower()

    for vpn_name, keywords in providers.items():
        for keyword in keywords:
            if keyword and keyword.lower() in text:
                return vpn_name, "keyword_match"

    if bool(online.get("proxy")):
        return "Proxy Service", "online_proxy_flag"
    if bool(online.get("hosting")):
        return "Hosting/VPN Infrastructure", "online_hosting_flag"

    return "Unknown VPN", "unresolved"


COMBINED_CSV_FIELDNAMES = [
        "ip",
        "sources",
        "raw_entries",
        "from_cidr",
        "provider",
        "provider_method",
        "chosen_source",
        "compare_notes",
        "local_score",
        "online_score",
        "country",
        "city",
        "latitude",
        "longitude",
        "isp",
        "asn",
        "as_org",
        "online_status",
        "online_message",
        "online_proxy",
        "online_hosting",
        "online_mobile",
        "local_country",
        "local_city",
        "local_latitude",
        "local_longitude",
        "local_isp",
        "local_asn",
        "local_as_org",
        "online_country",
        "online_city",
        "online_latitude",
        "online_longitude",
        "online_isp",
        "online_asn",
        "online_as_org",
]


def write_csv(output_path: Path, rows: List[Dict[str, object]]) -> None:
    write_rows_csv(output_path, COMBINED_CSV_FIELDNAMES, rows)


def main() -> None:
    args = parse_args()

    providers, asn_db = load_provider_data_from_app(Path(args.app_path))

    source_texts: Dict[str, str] = {}
    cache_dir = Path(args.cache_dir)

    for source_name, source_url in DEFAULT_SOURCES.items():
        try:
            source_texts[source_name] = download_with_cache(
                source_name,
                source_url,
                cache_dir,
                args.cache_max_age_hours,
                args.force_refresh,
                args.request_timeout,
            )
        except Exception as exc:
            print(f"[ERROR] Failed to fetch {source_name}: {exc}")
            source_texts[source_name] = ""

    ips, ip_meta = collect_candidate_ips(source_texts, args.samples_per_cidr)
    print(f"[COLLECT] Extracted {len(ips)} unique candidate IPv4 addresses")

    if args.max_ips and args.max_ips > 0 and len(ips) > args.max_ips:
        ips = ips[: args.max_ips]
        print(f"[COLLECT] Trimmed to first {len(ips)} IPs due to --max-ips")

    local_readers = init_local_readers(args)
    local_data = build_local_geolite2_records(ips, local_readers)

    local_rows = build_local_csv_rows(ips, ip_meta, local_data)
    local_output_path = Path(args.local_output)
    write_rows_csv(local_output_path, LOCAL_CSV_FIELDNAMES, local_rows)
    print(f"[LOCAL] Wrote {len(local_rows)} rows to {local_output_path}")

    print(f"[ONLINE] Enriching {len(ips)} IPs via ip-api batch endpoint")
    online_data = build_online_ip_api_records(ips, args.batch_size, args.request_timeout)

    online_rows = build_online_csv_rows(ips, ip_meta, online_data)
    online_output_path = Path(args.online_output)
    write_rows_csv(online_output_path, ONLINE_CSV_FIELDNAMES, online_rows)
    print(f"[ONLINE] Wrote {len(online_rows)} rows to {online_output_path}")

    rows: List[Dict[str, object]] = []
    provider_hits = 0

    for ip in ips:
        meta = ip_meta[ip]
        local = local_data.get(ip, {})
        online = online_data.get(
            ip,
            failed_online_record("missing_online_result"),
        )

        chosen_source, chosen, local_score, online_score, compare_notes = (
            compare_local_vs_online(local, online)
        )
        provider, provider_method = detect_provider(
            sorted(meta["sources"]), chosen, online, providers, asn_db
        )

        if provider != "Unknown VPN":
            provider_hits += 1

        rows.append(
            {
                "ip": ip,
                "sources": "|".join(sorted(meta["sources"])),
                "raw_entries": "|".join(sorted(meta["raw_entries"])),
                "from_cidr": bool(meta["from_cidr"]),
                "provider": provider,
                "provider_method": provider_method,
                "chosen_source": chosen_source,
                "compare_notes": compare_notes,
                "local_score": local_score,
                "online_score": online_score,
                "country": chosen.get("country", ""),
                "city": chosen.get("city", ""),
                "latitude": chosen.get("lat"),
                "longitude": chosen.get("lon"),
                "isp": chosen.get("isp", ""),
                "asn": chosen.get("asn", ""),
                "as_org": chosen.get("as_org", ""),
                "online_status": online.get("status", ""),
                "online_message": online.get("message", ""),
                "online_proxy": bool(online.get("proxy", False)),
                "online_hosting": bool(online.get("hosting", False)),
                "online_mobile": bool(online.get("mobile", False)),
                "local_country": local.get("country", ""),
                "local_city": local.get("city", ""),
                "local_latitude": local.get("lat"),
                "local_longitude": local.get("lon"),
                "local_isp": local.get("isp", ""),
                "local_asn": local.get("asn", ""),
                "local_as_org": local.get("as_org", ""),
                "online_country": online.get("country", ""),
                "online_city": online.get("city", ""),
                "online_latitude": online.get("lat"),
                "online_longitude": online.get("lon"),
                "online_isp": online.get("isp", ""),
                "online_asn": online.get("asn", ""),
                "online_as_org": online.get("as_org", ""),
            }
        )

    output_path = Path(args.output)
    write_csv(output_path, rows)

    close_local_readers(local_readers)

    print("\n[SUMMARY]")
    print(f"Rows written: {len(rows)}")
    print(f"Provider-resolved rows: {provider_hits}")
    print(f"Output CSV: {output_path}")
    print(f"Local CSV: {local_output_path}")
    print(f"Online CSV: {online_output_path}")


if __name__ == "__main__":
    main()
