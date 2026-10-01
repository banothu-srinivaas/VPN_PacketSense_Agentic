#!/usr/bin/env python3
"""Evaluate local GeoLite2 and online ip-api coordinate accuracy.

This script reads known IP reference coordinates, runs both enrichment functions
from build_vpn_dataset.py, computes haversine distance error, and writes two
report CSV files (local and online).
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from statistics import mean
from types import SimpleNamespace
from typing import Dict, List, Optional, Tuple

from build_vpn_dataset import (
    build_local_geolite2_records,
    build_online_ip_api_records,
    close_local_readers,
    haversine_km,
    init_local_readers,
)


LOCAL_REPORT_FIELDS = [
    "ip",
    "label",
    "expected_lat",
    "expected_lon",
    "actual_lat",
    "actual_lon",
    "distance_km",
    "tolerance_km",
    "within_tolerance",
    "country",
    "city",
    "status",
]

ONLINE_REPORT_FIELDS = LOCAL_REPORT_FIELDS + [
    "online_status",
    "online_message",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Test local GeoLite2 vs online ip-api coordinate accuracy"
    )
    parser.add_argument(
        "--cases",
        default="data/vpn_lists/known_ip_geo_cases.csv",
        help="CSV file with known IP coordinates",
    )
    parser.add_argument(
        "--local-report-output",
        default="data/vpn_lists/geo_accuracy_local.csv",
        help="Output CSV for local GeoLite2 accuracy report",
    )
    parser.add_argument(
        "--online-report-output",
        default="data/vpn_lists/geo_accuracy_online.csv",
        help="Output CSV for online ip-api accuracy report",
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
        "--batch-size",
        type=int,
        default=50,
        help="Batch size for ip-api lookups",
    )
    parser.add_argument(
        "--request-timeout",
        type=int,
        default=15,
        help="HTTP timeout in seconds",
    )
    parser.add_argument(
        "--max-cases",
        type=int,
        default=50,
        help="Maximum number of test cases to evaluate",
    )
    parser.add_argument(
        "--default-tolerance-km",
        type=float,
        default=2000.0,
        help="Fallback tolerance if a test case has no tolerance_km",
    )
    return parser.parse_args()


def to_float(value: object) -> Optional[float]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def load_known_cases(
    cases_path: Path, max_cases: int, default_tolerance_km: float
) -> List[Dict[str, object]]:
    if not cases_path.exists():
        raise FileNotFoundError(f"Cases file not found: {cases_path}")

    cases: List[Dict[str, object]] = []
    with cases_path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ip = str(row.get("ip", "")).strip()
            if not ip or ip.startswith("#"):
                continue

            expected_lat = to_float(row.get("expected_lat"))
            expected_lon = to_float(row.get("expected_lon"))
            if expected_lat is None or expected_lon is None:
                continue

            tolerance_km = to_float(row.get("tolerance_km"))
            if tolerance_km is None:
                tolerance_km = default_tolerance_km

            cases.append(
                {
                    "ip": ip,
                    "label": str(row.get("label", "") or "").strip() or ip,
                    "expected_lat": expected_lat,
                    "expected_lon": expected_lon,
                    "tolerance_km": tolerance_km,
                }
            )

            if len(cases) >= max_cases:
                break

    return cases


def evaluate_local_cases(
    cases: List[Dict[str, object]],
    local_records: Dict[str, Dict[str, object]],
) -> Tuple[List[Dict[str, object]], Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    distances: List[float] = []
    passed = 0
    missing_coords = 0

    for case in cases:
        ip = str(case["ip"])
        rec = local_records.get(ip, {})
        actual_lat = to_float(rec.get("lat"))
        actual_lon = to_float(rec.get("lon"))

        row = {
            "ip": ip,
            "label": case["label"],
            "expected_lat": case["expected_lat"],
            "expected_lon": case["expected_lon"],
            "actual_lat": actual_lat,
            "actual_lon": actual_lon,
            "distance_km": "",
            "tolerance_km": case["tolerance_km"],
            "within_tolerance": False,
            "country": rec.get("country", ""),
            "city": rec.get("city", ""),
            "status": "missing_coordinates",
        }

        if actual_lat is not None and actual_lon is not None:
            dist = haversine_km(
                float(case["expected_lat"]),
                float(case["expected_lon"]),
                actual_lat,
                actual_lon,
            )
            ok = dist <= float(case["tolerance_km"])
            row["distance_km"] = round(dist, 3)
            row["within_tolerance"] = ok
            row["status"] = "ok"
            distances.append(dist)
            if ok:
                passed += 1
        else:
            missing_coords += 1

        rows.append(row)

    evaluated = len(cases) - missing_coords
    summary = {
        "total_cases": len(cases),
        "evaluated": evaluated,
        "missing_coordinates": missing_coords,
        "passed": passed,
        "pass_rate": (passed / evaluated * 100.0) if evaluated > 0 else 0.0,
        "avg_distance_km": round(mean(distances), 3) if distances else None,
    }
    return rows, summary


def evaluate_online_cases(
    cases: List[Dict[str, object]],
    online_records: Dict[str, Dict[str, object]],
) -> Tuple[List[Dict[str, object]], Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    distances: List[float] = []
    passed = 0
    missing_coords = 0

    for case in cases:
        ip = str(case["ip"])
        rec = online_records.get(ip, {})
        actual_lat = to_float(rec.get("lat"))
        actual_lon = to_float(rec.get("lon"))

        row = {
            "ip": ip,
            "label": case["label"],
            "expected_lat": case["expected_lat"],
            "expected_lon": case["expected_lon"],
            "actual_lat": actual_lat,
            "actual_lon": actual_lon,
            "distance_km": "",
            "tolerance_km": case["tolerance_km"],
            "within_tolerance": False,
            "country": rec.get("country", ""),
            "city": rec.get("city", ""),
            "status": "missing_coordinates",
            "online_status": rec.get("status", ""),
            "online_message": rec.get("message", ""),
        }

        if actual_lat is not None and actual_lon is not None:
            dist = haversine_km(
                float(case["expected_lat"]),
                float(case["expected_lon"]),
                actual_lat,
                actual_lon,
            )
            ok = dist <= float(case["tolerance_km"])
            row["distance_km"] = round(dist, 3)
            row["within_tolerance"] = ok
            row["status"] = "ok"
            distances.append(dist)
            if ok:
                passed += 1
        else:
            missing_coords += 1

        rows.append(row)

    evaluated = len(cases) - missing_coords
    summary = {
        "total_cases": len(cases),
        "evaluated": evaluated,
        "missing_coordinates": missing_coords,
        "passed": passed,
        "pass_rate": (passed / evaluated * 100.0) if evaluated > 0 else 0.0,
        "avg_distance_km": round(mean(distances), 3) if distances else None,
    }
    return rows, summary


def write_report_csv(
    output_path: Path, fieldnames: List[str], rows: List[Dict[str, object]]
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main() -> None:
    args = parse_args()

    cases_path = Path(args.cases)
    cases = load_known_cases(cases_path, args.max_cases, args.default_tolerance_km)

    if not cases:
        print("[ERROR] No valid known-IP cases found. Check your --cases file.")
        return

    if len(cases) < 10 or len(cases) > 50:
        print(
            f"[WARN] Loaded {len(cases)} cases. Recommended range is 10-50 cases."
        )

    ips = [str(c["ip"]) for c in cases]
    print(f"[CASES] Loaded {len(ips)} known-IP coordinate test cases from {cases_path}")

    local_readers = init_local_readers(
        SimpleNamespace(city_db_path=args.city_db_path, asn_db_path=args.asn_db_path)
    )

    try:
        print(f"[LOCAL] Running GeoLite2 lookups for {len(ips)} IPs")
        local_records = build_local_geolite2_records(ips, local_readers)

        print(f"[ONLINE] Running ip-api lookups for {len(ips)} IPs")
        online_records = build_online_ip_api_records(
            ips,
            batch_size=args.batch_size,
            timeout=args.request_timeout,
        )
    finally:
        close_local_readers(local_readers)

    local_rows, local_summary = evaluate_local_cases(cases, local_records)
    online_rows, online_summary = evaluate_online_cases(cases, online_records)

    local_output = Path(args.local_report_output)
    online_output = Path(args.online_report_output)

    write_report_csv(local_output, LOCAL_REPORT_FIELDS, local_rows)
    write_report_csv(online_output, ONLINE_REPORT_FIELDS, online_rows)

    print("\n[LOCAL SUMMARY]")
    print(f"Total cases: {local_summary['total_cases']}")
    print(f"Evaluated: {local_summary['evaluated']}")
    print(f"Missing coordinates: {local_summary['missing_coordinates']}")
    print(f"Pass (within tolerance): {local_summary['passed']}")
    print(f"Pass rate: {local_summary['pass_rate']:.2f}%")
    print(f"Average distance error (km): {local_summary['avg_distance_km']}")
    print(f"Local report CSV: {local_output}")

    print("\n[ONLINE SUMMARY]")
    print(f"Total cases: {online_summary['total_cases']}")
    print(f"Evaluated: {online_summary['evaluated']}")
    print(f"Missing coordinates: {online_summary['missing_coordinates']}")
    print(f"Pass (within tolerance): {online_summary['passed']}")
    print(f"Pass rate: {online_summary['pass_rate']:.2f}%")
    print(f"Average distance error (km): {online_summary['avg_distance_km']}")
    print(f"Online report CSV: {online_output}")


if __name__ == "__main__":
    main()
