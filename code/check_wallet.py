#!/usr/bin/env python3
"""Compare a wallet's real Polymarket fills with the naive address-match count.

Polymarket's CTF Exchange emits one OrderFilled row per order. A wallet's own
fills are the rows where it is in the maker field. Rows where it appears in the
taker field belong to its counterparties. A parser that books those rows to the
wallet as well inflates its buys and sales. See NOTE-orderfilled-attribution.md.

Inputs (pick one):
  --jsonl FILE   the fills slice shipped in this repo (code/raw/fills_vandyke_txs.jsonl).
                 Only the named wallet is unredacted in it; other wallets need --csv or --rpc.
  --csv FILE     an export of OrderFilled rows with columns maker, taker, makerAssetId,
                 takerAssetId, makerAmountFilled, takerAmountFilled and a transaction hash
                 column (evt_tx_hash or transactionHash), plus fee and evt_index when present,
                 for example from Dune
  --rpc URL      fetch OrderFilled logs from a Polygon RPC that serves archive eth_getLogs,
                 together with --from-block and --to-block

Scope: the original CTF Exchange and NegRisk CTF Exchange contracts (USDC.e collateral).
Polymarket now trades on newer exchange contracts, which this script does not read.
Exchange fills only: redemptions, splits, merges and transfers are not counted.
Amounts are gross of fees; the fee total is printed separately. Pass the proxy wallet
that appears in the maker field, not the signing EOA.

Example:
  python3 -I code/check_wallet.py 0x31a56e9e690c621ed21de08cb559e9524cdb8ed9 \\
      --jsonl code/raw/fills_vandyke_txs.jsonl

Standard library only.
"""
import argparse
import csv
import json
import re
import sys
import time
import urllib.request

ORDER_FILLED = "0xd0a08e8c493f9c94f29311604c9de1b4e8c8d4c06bd0c789af57f2d65bfec0f6"
EXCHANGES = [
    "0x4bfb41d5b3570defd03c39a9a4d8de6bd8b8982e",  # CTF Exchange, original deployment (USDC.e)
    "0xc5d563a36ae78145c45a50134d48a1215220f80a",  # NegRisk CTF Exchange, original deployment (USDC.e)
]


def norm(addr):
    return str(addr).strip().lower()


def rows_from_jsonl(path):
    with open(path) as f:
        for line in f:
            if not line.strip():
                continue
            r = json.loads(line)
            if r.get("k", "OF") != "OF":
                continue
            yield dict(tx=r["tx"], li=r.get("li"), maker=norm(r["mk"]), taker=norm(r["tk"]),
                       ma=int(r["ma"]), ta=int(r["ta"]), mi=int(r["mi"]), ti=int(r["ti"]),
                       fee=int(r.get("f", 0) or 0))


def rows_from_csv(path):
    with open(path, newline="") as f:
        rd = csv.DictReader(f)
        cols = set(rd.fieldnames or [])
        txcol = next((c for c in ("evt_tx_hash", "transactionHash", "tx_hash") if c in cols), None)
        if txcol is None:
            raise SystemExit("CSV needs an evt_tx_hash or transactionHash column")
        licol = next((c for c in ("evt_index", "logIndex", "log_index") if c in cols), None)
        for r in rd:
            yield dict(tx=r[txcol], li=r[licol] if licol else None,
                       maker=norm(r["maker"]), taker=norm(r["taker"]),
                       ma=int(r["makerAssetId"]), ta=int(r["takerAssetId"]),
                       mi=int(r["makerAmountFilled"]), ti=int(r["takerAmountFilled"]),
                       fee=int(r.get("fee") or 0))


def rpc_call(url, method, params, retries=4):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, data=body, headers={"content-type": "application/json",
                                                                  "user-agent": "check_wallet/1.0"})
            out = json.load(urllib.request.urlopen(req, timeout=60))
            if "error" in out:
                raise RuntimeError(out["error"].get("message", str(out["error"])))
            return out["result"]
        except Exception as e:
            if attempt == retries - 1:
                raise
            time.sleep(2 * (attempt + 1))


def rows_from_rpc(url, wallet, start, end, chunk):
    topic = "0x" + "0" * 24 + wallet[2:]
    seen = set()
    for topics in ([ORDER_FILLED, None, topic], [ORDER_FILLED, None, None, topic]):
        b = start
        while b <= end:
            e = min(b + chunk - 1, end)
            logs = rpc_call(url, "eth_getLogs", [{"address": EXCHANGES, "fromBlock": hex(b),
                                                  "toBlock": hex(e), "topics": topics}])
            for lg in logs:
                key = (lg["transactionHash"], lg["logIndex"])
                if key in seen:
                    continue
                seen.add(key)
                d = lg["data"][2:]
                w = [int(d[i:i + 64], 16) for i in range(0, len(d), 64)]
                yield dict(tx=lg["transactionHash"], li=lg["logIndex"],
                           maker="0x" + lg["topics"][2][-40:], taker="0x" + lg["topics"][3][-40:],
                           ma=w[0], ta=w[1], mi=w[2], ti=w[3], fee=w[4] if len(w) > 4 else 0)
            b = e + 1


def attribute(rows, wallet):
    s = dict(own_rows=0, counterparty_rows=0, real_buy=0, real_sale=0, extra_buy=0, extra_sale=0,
             own_fees=0, self_matched=0, duplicates=0, own_txs=set(), counterparty_txs=set())
    seen = set()
    for r in rows:
        if r.get("li") is not None:
            key = (r["tx"], str(r["li"]))
            if key in seen:
                s["duplicates"] += 1
                continue
            seen.add(key)
        if r["maker"] == wallet and r["taker"] == wallet:
            s["self_matched"] += 1
        if r["maker"] == wallet:
            s["own_fees"] += r.get("fee", 0)
            s["own_rows"] += 1
            s["own_txs"].add(r["tx"])
            if r["ma"] == 0:          # wallet pays USDC.e, receives shares
                s["real_buy"] += r["mi"]
            else:                     # wallet gives shares, receives USDC.e
                s["real_sale"] += r["ti"]
        elif r["taker"] == wallet:
            s["counterparty_rows"] += 1
            s["counterparty_txs"].add(r["tx"])
            if r["ta"] == 0:          # counterparty sold shares: naive parser books a buy
                s["extra_buy"] += r["ti"]
            else:                     # counterparty bought shares: naive parser books a sale
                s["extra_sale"] += r["mi"]
    return s


def fmt(micro):
    return "{:,.2f}".format(micro / 1e6)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("wallet")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--jsonl")
    src.add_argument("--csv")
    src.add_argument("--rpc")
    ap.add_argument("--from-block", type=int)
    ap.add_argument("--to-block", type=int)
    ap.add_argument("--chunk", type=int, default=1000, help="blocks per eth_getLogs call (free public endpoints may need 50)")
    ap.add_argument("--json", action="store_true", help="print the result as JSON")
    a = ap.parse_args()

    wallet = norm(a.wallet)
    if not re.fullmatch(r"0x[0-9a-f]{40}", wallet):
        ap.error("wallet must be 0x followed by 40 hex characters")
    if a.jsonl:
        rows = rows_from_jsonl(a.jsonl)
    elif a.csv:
        rows = rows_from_csv(a.csv)
    else:
        if a.from_block is None or a.to_block is None:
            ap.error("--rpc needs --from-block and --to-block")
        rows = rows_from_rpc(a.rpc, wallet, a.from_block, a.to_block, a.chunk)

    s = attribute(rows, wallet)
    naive_buy = s["real_buy"] + s["extra_buy"]
    naive_sale = s["real_sale"] + s["extra_sale"]
    result = {
        "wallet": wallet,
        "own_rows": s["own_rows"],
        "own_transactions": len(s["own_txs"]),
        "counterparty_rows": s["counterparty_rows"],
        "real_buys_usdc": round(s["real_buy"] / 1e6, 6),
        "naive_buys_usdc": round(naive_buy / 1e6, 6),
        "real_sale_proceeds_usdc": round(s["real_sale"] / 1e6, 6),
        "naive_sale_proceeds_usdc": round(naive_sale / 1e6, 6),
        "buy_inflation_pct": round(100.0 * s["extra_buy"] / s["real_buy"], 2) if s["real_buy"] else None,
        "own_fees_usdc": round(s["own_fees"] / 1e6, 6),
        "self_matched_rows": s["self_matched"],
        "duplicate_rows_skipped": s["duplicates"],
    }
    if a.json:
        print(json.dumps(result, indent=2))
        return
    print("wallet %s" % wallet)
    print("  own fills (wallet in the maker field): %d rows in %d transactions" % (s["own_rows"], len(s["own_txs"])))
    print("  counterparty rows (wallet in the taker field): %d" % s["counterparty_rows"])
    print("                        real          naive count")
    print("  buys, USDC.e   %14s  %14s" % (fmt(s["real_buy"]), fmt(naive_buy)))
    print("  sales, USDC.e  %14s  %14s" % (fmt(s["real_sale"]), fmt(naive_sale)))
    if s["real_buy"]:
        print("  the naive count inflates buys by %.0f percent" % (100.0 * s["extra_buy"] / s["real_buy"]))
    print("  fees on own fills: %s USDC.e (amounts above are gross)" % fmt(s["own_fees"]))
    if s["self_matched"]:
        print("  warning: %d rows have the wallet as both maker and taker" % s["self_matched"])
    if s["duplicates"]:
        print("  skipped %d duplicate rows" % s["duplicates"])
    if not s["own_rows"] and not s["counterparty_rows"]:
        print("  warning: no rows for this wallet. Check that it is the proxy wallet in the maker field.", file=sys.stderr)


if __name__ == "__main__":
    main()
