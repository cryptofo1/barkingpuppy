#!/usr/bin/env python3
"""Compute holder distribution buckets for an Algorand ASA."""

from __future__ import annotations

import argparse
import json
import math
import sys
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Iterable, List


DEFAULT_THRESHOLDS = [0.01, 1.0, 5.0, 10.0]


@dataclass
class HolderBalance:
    address: str
    amount: int


def fetch_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:  # nosec B310
        return json.load(resp)


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


def run(asset_id: int, indexer_url: str, basis: str, thresholds: Iterable[float], page_size: int) -> None:
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

    print(f"Asset: {asset_id} | {name} {f'({unit})' if unit else ''}")
    print(f"Indexer: {indexer_url}")
    print(f"Decimals: {decimals}")
    print(f"Total holders (amount > 0): {holder_count:,}")
    print(f"Total circulating (sum of holder balances): {format_units(circulating, decimals)}")
    print(f"Configured total supply: {format_units(total, decimals)}")
    print(f"Bucket basis: {basis_label} = {format_units(basis_amount, decimals)}")
    print()
    print("Holder distribution by minimum balance threshold")
    print("threshold | minimum balance | holders | % of holders")
    print("--------- | --------------- | ------- | ------------")

    for threshold in thresholds:
        min_balance = math.ceil(basis_amount * (threshold / 100.0))
        count = sum(1 for h in holders if h.amount >= min_balance)
        pct = (count / holder_count) * 100.0
        print(
            f">= {threshold:g}% | {format_units(min_balance, decimals)} | "
            f"{count:,} | {pct:.4f}%"
        )

    print()
    print("Top 10 holders")
    print("rank | address | balance | share of basis")
    print("---- | ------- | ------- | -------------")
    for idx, holder in enumerate(holders[:10], start=1):
        share = (holder.amount / basis_amount) * 100.0 if basis_amount else 0.0
        print(
            f"{idx} | {holder.address} | {format_units(holder.amount, decimals)} | {share:.4f}%"
        )


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
        choices=["circulating", "asset-total"],
        help="Use circulating balances sum or configured asset total for thresholds.",
    )
    parser.add_argument(
        "--thresholds",
        default=",".join(str(x) for x in DEFAULT_THRESHOLDS),
        help="Comma-separated percentage thresholds. Example: 0.01,1,5,10",
    )
    parser.add_argument(
        "--page-size",
        default=1000,
        type=int,
        help="Balances page size (indexer max is usually 1000).",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        thresholds = parse_thresholds(args.thresholds)
        run(
            asset_id=args.asset_id,
            indexer_url=args.indexer_url,
            basis=args.basis,
            thresholds=thresholds,
            page_size=args.page_size,
        )
    except Exception as exc:  # pylint: disable=broad-except
        print(f"Failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
