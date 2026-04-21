#!/usr/bin/env python3
"""Compute holder distribution buckets for an Algorand ASA or ALGO."""

from __future__ import annotations

import argparse
import array
import bisect
import heapq
import json
import math
import sys
import time
import urllib.parse
import urllib.error
import urllib.request
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_CEILING
from http.client import IncompleteRead
from pathlib import Path
from typing import Iterable, List, Optional, Tuple


DEFAULT_THRESHOLDS = [0.01, 1.0, 5.0, 10.0]
DEFAULT_ACCOUNT_PERCENTILES = [0.01, 0.1, 0.2, 0.5, 1.0, 2.0, 3.0, 4.0, 5.0, 10.0]
DEFAULT_BALANCE_RANGES = (
    "0-1,1-10,10-100,100-1000,1000-10000,10000-50000,50000-100000,"
    "100000-500000,500000-1000000,1000000-5000000,5000000-inf"
)
ALGO_DECIMALS = 6
ALGO_UNIT = "ALGO"
MAX_RETRIES = 5
RETRY_SLEEP_SECONDS = 1.0


@dataclass
class HolderBalance:
    address: str
    amount: int


@dataclass
class BalanceRange:
    lower: Decimal
    upper: Optional[Decimal]


def _to_base_units(value: Decimal, decimals: int) -> int:
    scale = Decimal(10) ** decimals
    return int((value * scale).to_integral_value(rounding=ROUND_CEILING))


def _format_decimal_value(value: Decimal) -> str:
    normalized = value.normalize()
    if normalized == normalized.to_integral():
        return f"{int(normalized):,}"
    return f"{normalized:f}".rstrip("0").rstrip(".")


def fetch_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"accept": "application/json"})
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:  # nosec B310
                return json.load(resp)
        except urllib.error.HTTPError as exc:
            if exc.code not in (429, 500, 502, 503, 504):
                raise
            if attempt == MAX_RETRIES:
                raise RuntimeError(f"HTTP {exc.code} for {url}") from exc
        except (
            urllib.error.URLError,
            TimeoutError,
            ConnectionResetError,
            IncompleteRead,
            json.JSONDecodeError,
        ) as exc:
            if attempt == MAX_RETRIES:
                raise RuntimeError(f"Network error for {url}: {exc}") from exc
        time.sleep(RETRY_SLEEP_SECONDS * attempt)
    raise RuntimeError(f"Unable to fetch payload from {url}")


def get_asset(asset_id: int, indexer_url: str) -> dict:
    endpoint = f"{indexer_url.rstrip('/')}/v2/assets/{asset_id}?include-all=true"
    payload = fetch_json(endpoint)
    return payload["asset"]


def get_all_holders(asset_id: int, indexer_url: str, page_size: int) -> List[HolderBalance]:
    holders: List[HolderBalance] = []
    next_token = None

    while True:
        params = {
            "limit": str(page_size),
            "include-all": "false",
            "currency-greater-than": "0",
        }
        if next_token:
            params["next"] = next_token

        query = urllib.parse.urlencode(params)
        endpoint = f"{indexer_url.rstrip('/')}/v2/assets/{asset_id}/balances?{query}"
        payload = fetch_json(endpoint)

        for balance in payload.get("balances", []):
            amount = int(balance["amount"])
            if amount <= 0:
                continue
            holders.append(HolderBalance(address=balance["address"], amount=amount))

        next_token = payload.get("next-token")
        if not next_token:
            break

    return holders


def get_algo_supply(algod_url: str) -> dict:
    endpoint = f"{algod_url.rstrip('/')}/v2/ledger/supply"
    return fetch_json(endpoint)


def iterate_algo_holders(
    indexer_url: str, page_size: int, balance_field: str
) -> Iterable[HolderBalance]:
    next_token = None
    while True:
        params = {
            "limit": str(page_size),
            "include-all": "false",
            "currency-greater-than": "0",
            "exclude": "all",
        }
        if next_token:
            params["next"] = next_token
        query = urllib.parse.urlencode(params)
        endpoint = f"{indexer_url.rstrip('/')}/v2/accounts?{query}"
        payload = fetch_json(endpoint)
        for account in payload.get("accounts", []):
            amount = int(account[balance_field])
            if amount <= 0:
                continue
            yield HolderBalance(address=account["address"], amount=amount)
        next_token = payload.get("next-token")
        if not next_token:
            break


def _update_top_holders(top_heap: List[tuple[int, str]], holder: HolderBalance, size: int = 10) -> None:
    row = (holder.amount, holder.address)
    if len(top_heap) < size:
        heapq.heappush(top_heap, row)
        return
    if row[0] > top_heap[0][0]:
        heapq.heapreplace(top_heap, row)


def _print_report(
    asset_label: str,
    unit: str,
    indexer_url: str,
    decimals: int,
    holder_count: int,
    circulating: int,
    configured_total: int | None,
    basis_label: str,
    basis_amount: int,
    thresholds: Iterable[float],
    threshold_counts: List[int],
    top_holders: List[HolderBalance],
) -> None:
    print(f"Asset: {asset_label} {f'({unit})' if unit else ''}")
    print(f"Indexer: {indexer_url}")
    print(f"Decimals: {decimals}")
    print(f"Total holders (amount > 0): {holder_count:,}")
    print(f"Total circulating (sum of holder balances): {format_units(circulating, decimals)}")
    if configured_total is not None:
        print(f"Configured total supply: {format_units(configured_total, decimals)}")
    print(f"Bucket basis: {basis_label} = {format_units(basis_amount, decimals)}")
    print()
    print("Holder distribution by minimum balance threshold")
    print("threshold | minimum balance | holders | % of holders")
    print("--------- | --------------- | ------- | ------------")
    for threshold, count in zip(thresholds, threshold_counts):
        min_balance = math.ceil(basis_amount * (threshold / 100.0))
        pct = (count / holder_count) * 100.0 if holder_count else 0.0
        print(
            f">= {threshold:g}% | {format_units(min_balance, decimals)} | "
            f"{count:,} | {pct:.4f}%"
        )
    print()
    print("Top 10 holders")
    print("rank | address | balance | share of basis")
    print("---- | ------- | ------- | -------------")
    for idx, holder in enumerate(top_holders, start=1):
        share = (holder.amount / basis_amount) * 100.0 if basis_amount else 0.0
        print(f"{idx} | {holder.address} | {format_units(holder.amount, decimals)} | {share:.4f}%")


def _compute_percentile_cutoffs(amounts: List[int] | array.array, percentiles: List[float]) -> List[tuple[float, int, int]]:
    if not percentiles:
        return []
    holder_count = len(amounts)
    if holder_count == 0:
        return []
    try:
        import numpy as np  # pylint: disable=import-outside-toplevel
    except ImportError:  # pragma: no cover
        sorted_amounts = sorted(amounts, reverse=True)
        rows = []
        for pct in percentiles:
            account_count = max(1, math.ceil(holder_count * (pct / 100.0)))
            rows.append((pct, account_count, sorted_amounts[account_count - 1]))
        return rows

    np_amounts = np.frombuffer(amounts, dtype=np.uint64) if isinstance(amounts, array.array) else np.array(amounts, dtype=np.uint64)
    account_counts = [max(1, math.ceil(holder_count * (pct / 100.0))) for pct in percentiles]
    partition_indexes = [holder_count - n for n in account_counts]
    partitioned = np.partition(np_amounts.copy(), partition_indexes)
    rows = []
    for pct, account_count, idx in zip(percentiles, account_counts, partition_indexes):
        rows.append((pct, account_count, int(partitioned[idx])))
    return rows


def _print_account_percentile_table(
    percentiles: List[float], rows: List[tuple[float, int, int]], decimals: int, unit: str
) -> None:
    if not percentiles:
        return
    print()
    print("Percentage # Accounts Balance equals (or greater than)")
    print("Percentile | # Accounts | Balance (or greater)")
    print("---------- | ---------- | --------------------")
    for pct, account_count, cutoff in rows:
        unit_suffix = f" {unit}" if unit else ""
        print(f"{pct:g}% | {account_count:,} | {format_units(cutoff, decimals)}{unit_suffix}")


def _build_threshold_rows(
    thresholds: Iterable[float], threshold_counts: List[int], basis_amount: int, holder_count: int
) -> List[dict]:
    rows: List[dict] = []
    for threshold, count in zip(thresholds, threshold_counts):
        min_balance = math.ceil(basis_amount * (threshold / 100.0))
        pct = (count / holder_count) * 100.0 if holder_count else 0.0
        rows.append(
            {
                "threshold_percent": threshold,
                "minimum_balance": min_balance,
                "holders": count,
                "holder_percent": pct,
            }
        )
    return rows


def _build_percentile_rows(rows: List[tuple[float, int, int]]) -> List[dict]:
    return [
        {
            "percentile": percentile,
            "account_count": account_count,
            "minimum_balance": min_balance,
        }
        for percentile, account_count, min_balance in rows
    ]


def parse_balance_ranges(raw: str) -> List[BalanceRange]:
    ranges: List[BalanceRange] = []
    for item in raw.split(","):
        piece = item.strip()
        if not piece:
            continue
        if "-" not in piece:
            raise ValueError(f"Invalid range '{piece}', expected lower-upper.")
        lower_raw, upper_raw = piece.split("-", 1)
        try:
            lower = Decimal(lower_raw.strip())
        except InvalidOperation as exc:
            raise ValueError(f"Invalid lower bound in range '{piece}'") from exc
        upper_raw = upper_raw.strip().lower()
        if upper_raw in ("inf", "infinity", "+inf", "+infinity"):
            upper = None
        else:
            try:
                upper = Decimal(upper_raw)
            except InvalidOperation as exc:
                raise ValueError(f"Invalid upper bound in range '{piece}'") from exc
        if lower < 0:
            raise ValueError(f"Range lower bound must be >= 0: '{piece}'")
        if upper is not None and upper <= lower:
            raise ValueError(f"Range upper bound must be > lower bound: '{piece}'")
        ranges.append(BalanceRange(lower=lower, upper=upper))
    if not ranges:
        raise ValueError("At least one valid balance range is required.")
    for prev, curr in zip(ranges, ranges[1:]):
        if prev.upper is None:
            raise ValueError("Open-ended range must be last.")
        if curr.lower < prev.upper:
            raise ValueError(
                "Ranges must be non-overlapping and ordered by lower bound."
            )
    return ranges


def _convert_whole_to_base_units(value: Decimal, decimals: int) -> int:
    multiplier = Decimal(10) ** decimals
    return int((value * multiplier).to_integral_value(rounding=ROUND_CEILING))


def _compute_range_rows(
    amounts: List[int] | array.array,
    holder_count: int,
    decimals: int,
    ranges: List[BalanceRange],
) -> List[dict]:
    if not ranges or holder_count == 0:
        return []
    sorted_amounts = sorted(int(x) for x in amounts)
    rows = []
    for rng in ranges:
        lower_units = _convert_whole_to_base_units(rng.lower, decimals)
        upper_units = (
            _convert_whole_to_base_units(rng.upper, decimals)
            if rng.upper is not None
            else None
        )
        left = bisect.bisect_left(sorted_amounts, lower_units)
        right = (
            bisect.bisect_left(sorted_amounts, upper_units)
            if upper_units is not None
            else holder_count
        )
        count = max(0, right - left)
        total = sum(sorted_amounts[left:right]) if count else 0
        average = total // count if count else 0
        top_pct = (count / holder_count) * 100.0 if holder_count else 0.0
        rows.append(
            {
                "range_minimum_balance": lower_units,
                "range_maximum_balance": upper_units,
                "account_count": count,
                "holder_percent": top_pct,
                "average_balance": average,
                "top_percentile_cutoff": 0.0,
            }
        )
    cumulative = 0
    for row in reversed(rows):
        cumulative += row["account_count"]
        row["top_percentile_cutoff"] = (
            (cumulative / holder_count) * 100.0 if holder_count else 0.0
        )
    return rows


def _print_range_table(rows: List[dict], decimals: int, unit: str) -> None:
    if not rows:
        return
    unit_suffix = f" {unit}" if unit else ""
    print()
    print("Balance range summary")
    print("range | accounts | % holders | avg balance | top percentile")
    print("----- | -------- | --------- | ----------- | --------------")
    for row in rows:
        lower = format_units(row["range_minimum_balance"], decimals)
        upper_raw = row["range_maximum_balance"]
        upper = (
            format_units(upper_raw, decimals)
            if upper_raw is not None
            else "inf"
        )
        avg = format_units(row["average_balance"], decimals)
        pct = row["holder_percent"]
        print(
            f"{lower}-{upper}{unit_suffix} | {row['account_count']:,} | "
            f"{pct:.4f}% | {avg}{unit_suffix} | top {row['top_percentile_cutoff']:.4f}%"
        )


def _write_json_output(path: str, report: dict) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")


def format_units(amount: int, decimals: int) -> str:
    if decimals <= 0:
        return f"{amount:,}"
    base = 10**decimals
    whole = amount // base
    frac = amount % base
    frac_str = f"{frac:0{decimals}d}".rstrip("0")
    if not frac_str:
        return f"{whole:,}"
    return f"{whole:,}.{frac_str}"


def parse_thresholds(raw: str) -> List[float]:
    values = []
    for item in raw.split(","):
        val = float(item.strip())
        if val <= 0:
            raise ValueError(f"Threshold must be > 0: {val}")
        values.append(val)
    return sorted(set(values))


def _is_default_ranges(raw: str) -> bool:
    normalize = lambda s: "".join(s.lower().split())
    return normalize(raw) == normalize(DEFAULT_BALANCE_RANGES)


def run_asset(
    asset_id: int,
    indexer_url: str,
    basis: str,
    thresholds: Iterable[float],
    account_percentiles: List[float],
    balance_ranges: List[BalanceRange],
    page_size: int,
    output_format: str,
    output_file: str | None,
) -> None:
    asset = get_asset(asset_id, indexer_url=indexer_url)
    params = asset["params"]
    name = params.get("name", "(unknown)")
    unit = params.get("unit-name", "")
    total = int(params["total"])
    decimals = int(params.get("decimals", 0))

    holders = get_all_holders(asset_id, indexer_url=indexer_url, page_size=page_size)
    holders.sort(key=lambda h: h.amount, reverse=True)
    holder_count = len(holders)

    if holder_count == 0:
        print(f"Asset {asset_id} ({name}) has no live holders with positive balances.")
        return

    circulating = sum(h.amount for h in holders)
    basis_amount = total if basis == "asset-total" else circulating
    basis_label = "asset total supply" if basis == "asset-total" else "live circulating balances"
    threshold_counts = []
    for threshold in thresholds:
        min_balance = math.ceil(basis_amount * (threshold / 100.0))
        threshold_counts.append(sum(1 for h in holders if h.amount >= min_balance))
    top_holders = holders[:10]
    holder_amounts = [h.amount for h in holders]
    percentile_rows = _compute_percentile_cutoffs(holder_amounts, account_percentiles)
    range_rows = _compute_range_rows(
        amounts=holder_amounts,
        holder_count=holder_count,
        decimals=decimals,
        ranges=balance_ranges,
    )
    report = {
        "asset_id": asset_id,
        "asset_name": name,
        "asset_unit": unit,
        "indexer_url": indexer_url,
        "decimals": decimals,
        "holder_count": holder_count,
        "circulating": circulating,
        "configured_total_supply": total,
        "basis": basis,
        "basis_label": basis_label,
        "basis_amount": basis_amount,
        "threshold_rows": _build_threshold_rows(
            thresholds=thresholds,
            threshold_counts=threshold_counts,
            basis_amount=basis_amount,
            holder_count=holder_count,
        ),
        "top_holders": [{"address": h.address, "amount": h.amount} for h in top_holders],
        "account_percentile_rows": _build_percentile_rows(percentile_rows),
        "balance_range_rows": range_rows,
    }
    if output_file:
        _write_json_output(output_file, report)
    if output_format == "json":
        print(json.dumps(report, indent=2))
        return

    _print_report(
        asset_label=f"{asset_id} | {name}",
        unit=unit,
        indexer_url=indexer_url,
        decimals=decimals,
        holder_count=holder_count,
        circulating=circulating,
        configured_total=total,
        basis_label=basis_label,
        basis_amount=basis_amount,
        thresholds=thresholds,
        threshold_counts=threshold_counts,
        top_holders=top_holders,
    )
    _print_account_percentile_table(
        percentiles=account_percentiles,
        rows=percentile_rows,
        decimals=decimals,
        unit=unit,
    )
    _print_range_table(range_rows, decimals=decimals, unit=unit)


def run_algo(
    indexer_url: str,
    algod_url: str,
    basis: str,
    thresholds: List[float],
    account_percentiles: List[float],
    balance_ranges: List[BalanceRange],
    page_size: int,
    balance_field: str,
    output_format: str,
    output_file: str | None,
) -> None:
    supply = get_algo_supply(algod_url)
    total_money = int(supply["total-money"])

    top_heap: List[tuple[int, str]] = []
    holder_count = 0
    circulating = 0
    basis_label = "network total money" if basis == "network-total" else "live circulating balances"
    basis_amount = total_money if basis == "network-total" else 0
    min_balances = [math.ceil(basis_amount * (t / 100.0)) for t in thresholds] if basis == "network-total" else []
    threshold_counts = [0 for _ in thresholds]
    all_amounts = array.array("Q") if (account_percentiles or balance_ranges) else None

    for holder in iterate_algo_holders(indexer_url, page_size=page_size, balance_field=balance_field):
        holder_count += 1
        circulating += holder.amount
        _update_top_holders(top_heap, holder)
        if all_amounts is not None:
            all_amounts.append(holder.amount)
        if basis == "network-total":
            for idx, min_balance in enumerate(min_balances):
                if holder.amount >= min_balance:
                    threshold_counts[idx] += 1

    if holder_count == 0:
        print("ALGO has no live holders with positive balances.")
        return

    if basis != "network-total":
        # Circulating basis is only known after the first scan.
        basis_amount = circulating
        min_balances = [math.ceil(basis_amount * (t / 100.0)) for t in thresholds]
        for holder in iterate_algo_holders(indexer_url, page_size=page_size, balance_field=balance_field):
            for idx, min_balance in enumerate(min_balances):
                if holder.amount >= min_balance:
                    threshold_counts[idx] += 1

    top_holders = [
        HolderBalance(address=address, amount=amount)
        for amount, address in sorted(top_heap, key=lambda row: row[0], reverse=True)
    ]
    percentile_rows = _compute_percentile_cutoffs(all_amounts or [], account_percentiles)
    range_rows = _compute_range_rows(
        amounts=all_amounts or [],
        holder_count=holder_count,
        decimals=ALGO_DECIMALS,
        ranges=balance_ranges,
    )
    report = {
        "asset_id": 0,
        "asset_name": "Algorand",
        "asset_unit": ALGO_UNIT,
        "indexer_url": indexer_url,
        "decimals": ALGO_DECIMALS,
        "holder_count": holder_count,
        "circulating": circulating,
        "configured_total_supply": total_money,
        "basis": basis,
        "basis_label": basis_label,
        "basis_amount": basis_amount,
        "threshold_rows": _build_threshold_rows(
            thresholds=thresholds,
            threshold_counts=threshold_counts,
            basis_amount=basis_amount,
            holder_count=holder_count,
        ),
        "top_holders": [{"address": h.address, "amount": h.amount} for h in top_holders],
        "account_percentile_rows": _build_percentile_rows(percentile_rows),
        "balance_range_rows": range_rows,
    }
    if output_file:
        _write_json_output(output_file, report)
    if output_format == "json":
        print(json.dumps(report, indent=2))
        return

    _print_report(
        asset_label="0 | Algorand",
        unit=ALGO_UNIT,
        indexer_url=indexer_url,
        decimals=ALGO_DECIMALS,
        holder_count=holder_count,
        circulating=circulating,
        configured_total=total_money,
        basis_label=basis_label,
        basis_amount=basis_amount,
        thresholds=thresholds,
        threshold_counts=threshold_counts,
        top_holders=top_holders,
    )
    _print_account_percentile_table(
        percentiles=account_percentiles,
        rows=percentile_rows,
        decimals=ALGO_DECIMALS,
        unit=ALGO_UNIT,
    )
    _print_range_table(range_rows, decimals=ALGO_DECIMALS, unit=ALGO_UNIT)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compute Algorand ASA holder counts and bucket percentages."
    )
    parser.add_argument("--asset-id", required=True, type=int, help="Algorand ASA id.")
    parser.add_argument(
        "--indexer-url",
        default="https://mainnet-idx.algonode.cloud",
        help="Indexer API base URL.",
    )
    parser.add_argument(
        "--basis",
        default="circulating",
        choices=["circulating", "asset-total", "network-total"],
        help=(
            "Threshold basis. For ASA: circulating/asset-total. "
            "For ALGO (asset-id 0): circulating/network-total."
        ),
    )
    parser.add_argument(
        "--thresholds",
        default=",".join(str(x) for x in DEFAULT_THRESHOLDS),
        help="Comma-separated percentage thresholds. Example: 0.01,1,5,10",
    )
    parser.add_argument(
        "--account-percentiles",
        default=",".join(str(x) for x in DEFAULT_ACCOUNT_PERCENTILES),
        help=(
            "Comma-separated account percentile rows for cutoff table. "
            "Example: 0.01,0.1,0.2,0.5,1,2,3,4,5,10"
        ),
    )
    parser.add_argument(
        "--balance-ranges",
        default=DEFAULT_BALANCE_RANGES,
        help=(
            "Comma-separated balance ranges in whole-token units (lower-upper). "
            "Use 'inf' for open-ended upper bound."
        ),
    )
    parser.add_argument(
        "--page-size",
        default=1000,
        type=int,
        help="Balances page size (indexer max is usually 1000).",
    )
    parser.add_argument(
        "--algod-url",
        default="https://mainnet-api.algonode.cloud",
        help="Algod API base URL (used when asset-id is 0 for ALGO).",
    )
    parser.add_argument(
        "--algo-balance-field",
        default="amount",
        choices=["amount", "amount-without-pending-rewards"],
        help="Balance field used for ALGO rich list.",
    )
    parser.add_argument(
        "--output-format",
        default="text",
        choices=["text", "json"],
        help="Output format for stdout.",
    )
    parser.add_argument(
        "--output-file",
        help="Optional path to write structured JSON output.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        thresholds = parse_thresholds(args.thresholds)
        account_percentiles = parse_thresholds(args.account_percentiles)
        balance_ranges = parse_balance_ranges(args.balance_ranges)
        if args.asset_id != 0 and _is_default_ranges(args.balance_ranges):
            # Token-agnostic defaults are tuned for ALGO scale and are too large for many ASAs.
            balance_ranges = parse_balance_ranges("0-1,1-10,10-100,100-1000,1000-10000,10000-inf")
        if args.asset_id == 0:
            if args.basis == "asset-total":
                raise ValueError("For ALGO (asset-id 0), basis must be circulating or network-total.")
            run_algo(
                indexer_url=args.indexer_url,
                algod_url=args.algod_url,
                basis=args.basis,
                thresholds=thresholds,
                account_percentiles=account_percentiles,
                balance_ranges=balance_ranges,
                page_size=args.page_size,
                balance_field=args.algo_balance_field,
                output_format=args.output_format,
                output_file=args.output_file,
            )
        else:
            if args.basis == "network-total":
                raise ValueError("network-total basis is only valid for ALGO (asset-id 0).")
            run_asset(
                asset_id=args.asset_id,
                indexer_url=args.indexer_url,
                basis=args.basis,
                thresholds=thresholds,
                account_percentiles=account_percentiles,
                balance_ranges=balance_ranges,
                page_size=args.page_size,
                output_format=args.output_format,
                output_file=args.output_file,
            )
    except Exception as exc:  # pylint: disable=broad-except
        print(f"Failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
