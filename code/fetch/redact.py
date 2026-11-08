#!/usr/bin/env python3
"""redact.py: turn the network outputs in fetch/out/ into the files shipped in code/raw/.

Offline step. Stdlib only.

Every 20-byte address in the inputs is replaced by a label, except the wallet named in
the CFTC complaint (0x31a56e9e690c621ed21de08cb559e9524cdb8ed9), which is kept as is.

  public contracts      -> their names (USDC.e, CTFExchange, ConditionalTokens, POLToken)
  every other address   -> anon-TT-NN, where TT numbers the transaction and NN the address
                           within it, both in order of first appearance

Labels are scoped to one transaction. The same address in two transactions gets two labels,
so no count across transactions can be made from the shipped files.

An address appears in three shapes: a bare 0x string of 40 hex digits, a 32-byte topic
(24 zero digits then the address), and a 32-byte word inside a log data field. Topics are
replaced by the label. A data field that holds an address word is replaced by a list of
its 32-byte words with the address word replaced by the label.

Before redacting, the fills slice is cut from the full scan when it is not already in the
source folder: out/fills.jsonl -> out/fills_vandyke_txs.jsonl keeps every OrderFilled row in
the transactions where the named wallet is maker or taker, in scan order, without duplicates.

Usage:
  python3 code/fetch/redact.py [--src code/fetch/out] [--dst code/raw]
"""
import argparse
import hashlib
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
SUBJECT = "0x31a56e9e690c621ed21de08cb559e9524cdb8ed9"
# Public contracts, keyed by the SHA-256 of the lowercase 0x address string, so that no
# address other than the named wallet is written in this repository.
CONTRACTS = {
    "0922fb7af6f5f4581013104a03954957a40bc898fe14588e5cf0334c1f6e6662": "USDC.e",
    "6eb37c44cab105b61577ec85402c905435b3bf7b951de5712a54ba88081afee6": "CTFExchange",
    "183d8420dc12b39b58fe43b075f4456e0bd4cd9191d701af7fb54069056b69ee": "ConditionalTokens",
    "24d5419398851d11fccf1567d4358f56de6b49550e348813acfe73dfbea796d6": "POLToken",
}
HEX40 = re.compile(r"^0x[0-9a-fA-F]{40}$")
FILES = ["receipts_15tx.json", "receipts_redeems.json", "dataapi_activity.json",
         "token_map.json", "block_ts.json", "fills_vandyke_txs.jsonl"]


class Labeler:
    def __init__(self):
        self.map = {}
        self.txs = {}
        self.n = 0

    def label(self, addr, tx):
        a = addr.lower()
        if a == SUBJECT:
            return SUBJECT
        name = CONTRACTS.get(hashlib.sha256(a.encode()).hexdigest())
        if name:
            return name
        if tx is None:
            raise ValueError("address outside a transaction: cannot scope its label")
        if tx not in self.txs:
            self.txs[tx] = [len(self.txs) + 1, 0]
        key = (tx, a)
        if key not in self.map:
            self.txs[tx][1] += 1
            self.n += 1
            self.map[key] = "anon-%02d-%02d" % tuple(self.txs[tx])
        return self.map[key]


def is_addr_word(w):
    """A data word that holds an address. Amounts and balances also start with zeros, so a
    data word counts only if its value is above 2**150. In these logs the only address in a
    data field is the collateral token of PositionSplit (USDC.e)."""
    return len(w) == 64 and w[:24] == "0" * 24 and int(w, 16) > 2 ** 150


def is_addr_topic(w):
    """An indexed topic that holds an address: 24 zero digits, then a nonzero address."""
    return len(w) == 64 and w[:24] == "0" * 24 and int(w, 16) > 0


def redact_value(v, lab, key=None, tx=None):
    """tx is the transaction the value belongs to: the transactionHash of the enclosing
    receipt or log, or the tx field of a fills row."""
    if isinstance(v, dict):
        t = v.get("transactionHash") or v.get("tx")
        if isinstance(t, str):
            tx = t.lower()
        return {k: redact_value(x, lab, k, tx) for k, x in v.items()}
    if isinstance(v, list):
        return [redact_value(x, lab, key, tx) for x in v]
    if not isinstance(v, str):
        return v
    if HEX40.match(v):
        return lab.label(v, tx)
    if key == "topics" and len(v) == 66 and is_addr_topic(v[2:]):
        return lab.label("0x" + v[-40:], tx)
    if key == "data" and v.startswith("0x") and len(v) > 2 and (len(v) - 2) % 64 == 0:
        words = [v[2 + i:66 + i] for i in range(0, len(v) - 2, 64)]
        if any(is_addr_word(w) for w in words):
            return [lab.label("0x" + w[-40:], tx) if is_addr_word(w) else w for w in words]
    return v


def cut_slice(src):
    """Write src/fills_vandyke_txs.jsonl from src/fills.jsonl (output of polymarket_fetch.py --scan)."""
    full = os.path.join(src, "fills.jsonl")
    out = os.path.join(src, "fills_vandyke_txs.jsonl")
    if os.path.exists(out) or not os.path.exists(full):
        return
    rows, seen = [], set()
    with open(full) as f:
        for line in f:
            if not line.strip():
                continue
            r = json.loads(line)
            key = (r["tx"], r["li"])
            if r.get("k") != "OF" or key in seen:
                continue
            seen.add(key)
            rows.append(r)
    txs = {r["tx"] for r in rows if SUBJECT in (r["mk"].lower(), (r["tk"] or "").lower())}
    with open(out, "w") as fo:
        for r in rows:
            if r["tx"] in txs:
                fo.write(json.dumps(r) + "\n")
    print("cut %s: %d transactions" % (out, len(txs)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=os.path.join(HERE, "out"))
    ap.add_argument("--dst", default=os.path.join(os.path.dirname(HERE), "raw"))
    a = ap.parse_args()
    cut_slice(a.src)
    lab = Labeler()
    os.makedirs(a.dst, exist_ok=True)
    # fills first, so transaction numbering follows the order of the slice
    for name in ["fills_vandyke_txs.jsonl"] + [f for f in FILES if not f.endswith(".jsonl")]:
        src = os.path.join(a.src, name)
        if not os.path.exists(src):
            print("missing", src)
            continue
        dst = os.path.join(a.dst, name)
        if name.endswith(".jsonl"):
            with open(src) as fi, open(dst, "w") as fo:
                for line in fi:
                    if line.strip():
                        fo.write(json.dumps(redact_value(json.loads(line), lab)) + "\n")
        else:
            d = redact_value(json.load(open(src)), lab)
            with open(dst, "w") as fo:
                json.dump(d, fo, indent=1)
                fo.write("\n")
        print("wrote", dst)
    print("labels assigned: %d" % lab.n)


if __name__ == "__main__":
    main()
