"""Tests for the maker rule in code/check_wallet.py.

Standard library only. Run from the repository root:
  python3 -I -m unittest discover -s tests -v
"""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "code"))
import check_wallet as cw  # noqa: E402

WALLET = "0x31a56e9e690c621ed21de08cb559e9524cdb8ed9"
SLICE = os.path.join(ROOT, "code", "raw", "fills_vandyke_txs.jsonl")
EXCHANGE = "ctfexchange"
MAKER = "0x" + "ab" * 20
YES, NO = 111, 222  # synthetic outcome token ids; 0 is USDC.e


def row(tx, li, maker, taker, ma, ta, mi, ti, fee=0):
    """One OrderFilled row in the shape the readers in check_wallet.py yield."""
    return dict(tx=tx, li=li, maker=cw.norm(maker), taker=cw.norm(taker),
                ma=ma, ta=ta, mi=mi, ti=ti, fee=fee)


def mint_match():
    """Modelled on tx 0x845d5e6b: the wallet buys 87.5 Yes for 7.00 USDC.e as taker,
    one maker buys 87.5 No for 80.50. The exchange emits the maker row with the wallet
    in the taker field, and the wallet's own row with the exchange in the taker field."""
    return [row("0xa", 1, MAKER, WALLET, 0, NO, 80_500_000, 87_500_000),
            row("0xa", 2, WALLET, EXCHANGE, 0, YES, 7_000_000, 87_500_000)]


def merge_match():
    """The wallet sells 10 Yes for 1.76 as taker, one maker sells 10 No for 8.24 into
    the merge. The maker row gives No shares and gets USDC.e."""
    return [row("0xb", 1, MAKER, WALLET, NO, 0, 10_000_000, 8_240_000),
            row("0xb", 2, WALLET, EXCHANGE, YES, 0, 10_000_000, 1_760_000)]


class SyntheticMatches(unittest.TestCase):
    def test_mint_match_books_only_the_own_row(self):
        s = cw.attribute(mint_match(), WALLET)
        self.assertEqual(s["own_rows"], 1)
        self.assertEqual(s["counterparty_rows"], 1)
        self.assertEqual(s["real_buy"], 7_000_000)
        self.assertEqual(s["real_sale"], 0)
        # a taker field parser would book the maker's 80.50 No purchase as a sale
        self.assertEqual(s["extra_sale"], 80_500_000)
        self.assertEqual(s["extra_buy"], 0)

    def test_merge_match_books_only_the_own_row(self):
        s = cw.attribute(merge_match(), WALLET)
        self.assertEqual(s["real_sale"], 1_760_000)
        self.assertEqual(s["real_buy"], 0)
        # a taker field parser would book the maker's No sale as a buy of 8.24
        self.assertEqual(s["extra_buy"], 8_240_000)
        self.assertEqual(s["extra_sale"], 0)

    def test_duplicate_tx_and_log_index_counted_once(self):
        rows = mint_match() + mint_match()
        s = cw.attribute(rows, WALLET)
        self.assertEqual(s["duplicates"], 2)
        self.assertEqual(s["own_rows"], 1)
        self.assertEqual(s["real_buy"], 7_000_000)

    def test_mixed_case_address_matches(self):
        upper = "0x" + WALLET[2:].upper()
        rows = [row("0xa", 1, MAKER, upper, 0, NO, 80_500_000, 87_500_000),
                row("0xa", 2, upper, EXCHANGE, 0, YES, 7_000_000, 87_500_000)]
        s = cw.attribute(rows, cw.norm(upper))
        self.assertEqual(s["own_rows"], 1)
        self.assertEqual(s["real_buy"], 7_000_000)

    def test_mixed_case_address_in_jsonl_file(self):
        upper = "0x" + WALLET[2:].upper()
        line = {"k": "OF", "tx": "0xa", "li": 2, "mk": upper, "tk": EXCHANGE,
                "ma": 0, "ta": YES, "mi": 7_000_000, "ti": 87_500_000, "f": 0}
        with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False) as f:
            f.write(json.dumps(line) + "\n")
        try:
            s = cw.attribute(cw.rows_from_jsonl(f.name), WALLET)
        finally:
            os.unlink(f.name)
        self.assertEqual(s["real_buy"], 7_000_000)

    def test_wallet_with_no_rows(self):
        s = cw.attribute(mint_match(), "0x" + "cd" * 20)
        for key in ("own_rows", "counterparty_rows", "real_buy", "real_sale",
                    "extra_buy", "extra_sale"):
            self.assertEqual(s[key], 0, key)


class ShippedSlice(unittest.TestCase):
    """Expected values were read from the output of check_wallet.attribute on the
    shipped slice, and agree with section 7 of code/recompute.py."""

    def test_slice_hash_matches_sha256sums(self):
        with open(os.path.join(ROOT, "data", "SHA256SUMS")) as f:
            pins = {line.split()[1]: line.split()[0] for line in f if line.strip()}
        with open(SLICE, "rb") as f:
            digest = hashlib.sha256(f.read()).hexdigest()
        self.assertEqual(digest, pins["../code/raw/fills_vandyke_txs.jsonl"])

    def test_real_and_misbooked_amounts(self):
        s = cw.attribute(cw.rows_from_jsonl(SLICE), WALLET)
        self.assertEqual(s["own_rows"], 15)
        self.assertEqual(len(s["own_txs"]), 15)
        self.assertEqual(s["counterparty_rows"], 253)
        self.assertEqual(s["real_buy"], 33_934_339_992)
        self.assertEqual(s["real_sale"], 5_857_902_080)
        self.assertEqual(s["extra_buy"], 16_699_747_428)
        self.assertEqual(s["extra_sale"], 347_865_643_364)

    def test_taker_field_booking_overstates_buys_by_49_percent(self):
        s = cw.attribute(cw.rows_from_jsonl(SLICE), WALLET)
        self.assertEqual(round(100 * s["extra_buy"] / s["real_buy"]), 49)

    def test_command_line_json_output(self):
        out = subprocess.run(
            [sys.executable, "-I", os.path.join(ROOT, "code", "check_wallet.py"),
             WALLET.upper().replace("0X", "0x"), "--jsonl", SLICE, "--json"],
            capture_output=True, text=True, check=True).stdout
        r = json.loads(out)
        self.assertEqual(r["real_buys_usdc"], 33934.339992)
        self.assertEqual(r["naive_buys_usdc"], 50634.08742)
        self.assertEqual(r["buy_inflation_pct"], 49.21)


if __name__ == "__main__":
    unittest.main()
