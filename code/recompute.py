#!/usr/bin/env python3
"""recompute.py: recompute every figure in README.md and NOTE-orderfilled-attribution.md.

Offline. Stdlib only. Reads the shipped files in code/raw/ and nothing else:
  receipts_15tx.json, receipts_redeems.json, dataapi_activity.json,
  fills_vandyke_txs.jsonl, token_map.json, block_ts.json

Usage:
  python3 -I code/recompute.py              print every figure and check
  python3 -I code/recompute.py --out DIR    also write the four data/ CSVs into DIR

Cash comes from USDC.e Transfer logs in the transaction receipts. Share counts come from
Polymarket's public activity API (dataapi_activity.json). Times are shown in UTC and in
US Eastern time, which was EST (UTC minus 5 hours) on every date involved.
Exit status is 0 only if every check passes.
"""
import argparse
import csv
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw")

W = "0x31a56e9e690c621ed21de08cb559e9524cdb8ed9"
TRANSFER = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
POSITION_SPLIT = "0x2e6bb91f8cbcda0c93623c54d0403a43514fabc40084ec96b6d5379a74786298"
JAN31 = "maduro-out-by-january-31-2026-318"
EST = timezone(timedelta(hours=-5))

FAILS = []


def check(name, ok, detail=""):
    print("  [%s] %s%s" % ("PASS" if ok else "FAIL", name, (" (" + detail + ")") if detail else ""))
    if not ok:
        FAILS.append(name)


def load(name):
    with open(os.path.join(RAW, name)) as f:
        return json.load(f)


def who(x):
    """Topic or address field to a comparable key. Redacted entries are labels."""
    if isinstance(x, str) and x.startswith("0x") and len(x) == 66:
        return "0x" + x[-40:]
    return x


def usd(micro):
    """Micro USDC.e (integer) to a string with cents, rounded half up."""
    cents = (micro + 5000) // 10000
    return "{:,}.{:02d}".format(cents // 100, cents % 100)


def usd6(micro):
    return "%d.%06d" % (micro // 10 ** 6, micro % 10 ** 6)


def et(ts):
    return datetime.fromtimestamp(ts, EST).strftime("%Y-%m-%d %H:%M:%S ET")


def utc(ts):
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")


def hms(sec):
    return "%dh%02dm%02ds" % (sec // 3600, sec % 3600 // 60, sec % 60)


def usdc_flows(receipt):
    """Return (out_from_W, in_to_W, list of all USDC.e transfers) in micro USDC.e."""
    out = inn = 0
    allt = []
    for lg in receipt["logs"]:
        if lg["address"] != "USDC.e" or lg["topics"][0] != TRANSFER:
            continue
        frm, to = who(lg["topics"][1]), who(lg["topics"][2])
        amt = int(lg["data"], 16)
        allt.append((frm, to, amt))
        if frm == W:
            out += amt
        if to == W:
            inn += amt
    return out, inn, allt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", help="write data CSVs into this directory")
    args = ap.parse_args()

    rec15 = load("receipts_15tx.json")
    recred = load("receipts_redeems.json")
    act = load("dataapi_activity.json")
    tmap = load("token_map.json")
    bts = load("block_ts.json")
    fills = []
    with open(os.path.join(RAW, "fills_vandyke_txs.jsonl")) as f:
        for line in f:
            if line.strip():
                fills.append(json.loads(line))
    act_by_tx = {a["transactionHash"]: a for a in act}

    # ------------------------------------------------------------ 1. inputs
    print("1. Inputs")
    check("15 trade receipts, 2 redemption receipts", len(rec15) == 15 and len(recred) == 2)
    types = defaultdict(int)
    for a in act:
        types[a["type"]] += 1
    check("activity API rows: 15 TRADE + 2 REDEEM", dict(types) == {"TRADE": 15, "REDEEM": 2}, str(dict(types)))
    check("all 17 activity rows belong to the wallet", all(a["proxyWallet"] == W for a in act))
    for r in rec15 + recred:
        b = int(r["blockNumber"], 16)
        lts = {int(lg["blockTimestamp"], 16) for lg in r["logs"]}
        if str(b) not in bts or lts != {bts[str(b)]["ts"]}:
            check("block_ts.json agrees with receipt blockTimestamp, block %d" % b, False)
            break
    else:
        check("block_ts.json has all 17 receipt blocks and agrees with the receipts' blockTimestamp", True)
    check("every receipt status is success", all(r["status"] == "0x1" for r in rec15 + recred))

    # ------------------------------------------------------------ 2. per transaction table
    print("\n2. Transactions (cash from receipts, shares from the activity API)")
    rows = []
    for r in rec15 + recred:
        tx = r["transactionHash"]
        a = act_by_tx[tx]
        b = int(r["blockNumber"], 16)
        ts = bts[str(b)]["ts"]
        out, inn, _ = usdc_flows(r)
        kind = "REDEEM" if a["type"] == "REDEEM" else a["side"]
        rows.append(dict(tx=tx, block=b, ts=ts, kind=kind, slug=a["slug"], outcome=a["outcome"],
                         shares=a["size"], api_usdc=a["usdcSize"], out=out, inn=inn))
    rows.sort(key=lambda x: (x["ts"], x["tx"]))
    print("  %-2s %-12s %-22s %-6s %-48s %14s %13s %13s" % ("n", "tx", "time ET", "type", "market", "shares", "USDC.e out", "USDC.e in"))
    for i, x in enumerate(rows, 1):
        x["n"] = i
        print("  %-2d %-12s %-22s %-6s %-48s %14s %13s %13s" % (
            i, x["tx"][:10], et(x["ts"])[:19], x["kind"], x["slug"][:48], "{:,.2f}".format(x["shares"]),
            usd(x["out"]) if x["out"] else "", usd(x["inn"]) if x["inn"] else ""))
    api_ok = all(abs(x["api_usdc"] * 1e6 - (x["out"] or x["inn"])) < 1.5 for x in rows)
    check("activity API usdcSize equals the receipt USDC.e amount for all 17 rows (to 1 micro USDC.e)", api_ok)
    one_sided = all((x["out"] == 0) != (x["inn"] == 0) for x in rows)
    check("each transaction moves USDC.e in one direction only for the wallet", one_sided)

    buys = [x for x in rows if x["kind"] == "BUY"]
    sells = [x for x in rows if x["kind"] == "SELL"]
    reds = [x for x in rows if x["kind"] == "REDEEM"]
    buy_total = sum(x["out"] for x in buys)
    sell_total = sum(x["inn"] for x in sells)
    red_total = sum(x["inn"] for x in reds)
    proceeds = sell_total + red_total
    net = proceeds - buy_total
    print("\n3. Totals")
    print("  buy transactions: %d, USDC.e out %s (%s)" % (len(buys), usd(buy_total), usd6(buy_total)))
    print("  sell transactions: %d, USDC.e in %s" % (len(sells), usd(sell_total)))
    for x in sells:
        print("    sell %s: %s shares for %s (%.4f per share)" % (x["slug"][:40], "{:,.2f}".format(x["shares"]), usd(x["inn"]), x["inn"] / 1e6 / x["shares"]))
    print("  redemptions: %d, USDC.e in %s" % (len(reds), usd(red_total)))
    for x in reds:
        print("    redeem %s: %s" % (x["slug"][:40], usd(x["inn"])))
    print("  proceeds (sells + redemptions): %s" % usd(proceeds))
    print("  net (proceeds minus buys): %s" % usd(net))
    check("13 buys = indictment para 11 '13 separate occasions'", len(buys) == 13)
    check("buys 33,934.34 vs indictment para 10 'approximately $33,934'", usd(buy_total) == "33,934.34")
    check("net 409,880.95 vs indictment para 15 'approximately $409,881'", usd(net) == "409,880.95")

    jb = [x for x in buys if x["slug"] == JAN31]
    j_sh = sum(x["shares"] for x in jb)
    j_cost = sum(x["out"] for x in jb)
    j_red = sum(x["inn"] for x in reds if x["slug"] == JAN31)
    print("  January Contract buys: %d txs, %s shares, cost %s, average %.5f" % (len(jb), "{:,.2f}".format(j_sh), usd(j_cost), j_cost / 1e6 / j_sh))
    print("  January Contract redemption %s, net %s" % (usd(j_red), usd(j_red - j_cost)))
    check("jan31 shares > 436,000, cost ~32,538, avg ~0.074 (complaint para 52)",
          436000 < j_sh < 437000 and usd(j_cost) == "32,538.34" and round(j_cost / 1e6 / j_sh, 3) == 0.074)
    check("jan31 net 404,221.27 vs complaint para 53 'more than $404,000'", usd(j_red - j_cost) == "404,221.27")
    others_net = proceeds - j_red - (buy_total - j_cost)
    print("  other three contracts net: %s (complaint para 55 'more than $5,000')" % usd(others_net))
    check("other three contracts net > 5,000 (complaint para 55)", others_net > 5000 * 10 ** 6)

    # ------------------------------------------------------------ 4. funding ladder
    print("\n4. January Contract funding ladder vs complaint para 50 (times from the activity API)")

    def group(ts):
        d = datetime.fromtimestamp(ts, EST)
        part = "morning" if d.hour < 12 else "evening"
        return "%s %s" % (d.strftime("%b %d").replace(" 0", " "), part)

    para50 = {"Dec 30 evening": "approximately 14,600 shares across two transactions",
              "Jan 1 evening": "73,700 shares",
              "Jan 2 morning": "approximately 90,300 shares",
              "Jan 2 evening": "more than 250,000 shares across three transactions between 8:30 and 10:00 PM ET"}
    ladder = []
    for g in para50:
        xs = [x for x in jb if group(x["ts"]) == g]
        ladder.append(dict(group=g, n=len(xs), times=" / ".join(et(x["ts"])[11:16] for x in xs),
                           shares=sum(x["shares"] for x in xs), usdc=sum(x["out"] for x in xs), para50=para50[g]))
    cum = 0.0
    for l in ladder:
        cum += l["shares"]
        l["cum"] = cum
        print("  %-15s %d tx at %-22s %12s shares, %10s USDC.e, cumulative %12s | para 50: %s" % (
            l["group"], l["n"], l["times"], "{:,.2f}".format(l["shares"]), usd(l["usdc"]), "{:,.2f}".format(cum), l["para50"]))
    check("ladder covers all 7 January Contract buys", sum(l["n"] for l in ladder) == 7)
    L = {l["group"]: l for l in ladder}
    check("ladder matches para 50",
          L["Dec 30 evening"]["n"] == 2 and round(L["Dec 30 evening"]["shares"], -2) == 14600
          and round(L["Jan 1 evening"]["shares"], -2) == 73700
          and round(L["Jan 2 morning"]["shares"], -2) == 90300
          and L["Jan 2 evening"]["n"] == 3 and L["Jan 2 evening"]["shares"] > 250000
          and all("20:30" <= et(x["ts"])[11:16] <= "22:00" for x in jb if group(x["ts"]) == "Jan 2 evening"))

    # ------------------------------------------------------------ 5. indictment para 11 groups
    print("\n5. Indictment para 11 dollar groups")
    by_day = defaultdict(list)
    for x in buys:
        by_day[group(x["ts"])].append(x)
    for g in sorted(by_day, key=lambda k: min(x["ts"] for x in by_day[k])):
        xs = by_day[g]
        print("  %-15s %s = %s" % (g, " + ".join(usd(x["out"]) for x in xs), usd(sum(x["out"] for x in xs))))
    j2e = sorted(by_day["Jan 2 evening"], key=lambda x: x["ts"])
    print("  Jan 2 evening in order: %s" % ", ".join("%s %s" % (et(x["ts"])[11:19], usd(x["out"])) for x in j2e))
    gap = j2e[2]["ts"] - j2e[1]["ts"]
    print("  the $50.00 US forces buy precedes the $7,000.00 buy by %d seconds" % gap)
    print("  the $7,215.00 buy follows the $7,000.00 buy by %s (indictment: approximately 45 minutes)" % hms(j2e[3]["ts"] - j2e[2]["ts"]))
    check("11(c) Jan 1 = 6,100.00", usd(sum(x["out"] for x in by_day["Jan 1 evening"])) == "6,100.00")
    check("11(d) Jan 2 morning = 6,150.00", usd(sum(x["out"] for x in by_day["Jan 2 morning"])) == "6,150.00")
    check("11(d) evening: 6,000.00 then 50.00 + 7,000.00 = 7,050.00 then 7,215.00",
          [usd(x["out"]) for x in j2e] == ["6,000.00", "50.00", "7,000.00", "7,215.00"])
    early = by_day["Jan 2 morning"][0]
    print("  note: the first Jan 2 'morning' buy (%s) executed at %s" % (usd(early["out"]), et(early["ts"])))

    # ------------------------------------------------------------ 6. redemption timing and residuals
    print("\n6. Redemption timing and residuals")
    ann = int(datetime(2026, 1, 3, 4, 21, tzinfo=EST).timestamp())
    res = int(datetime(2026, 1, 3, 7, 14, tzinfo=EST).timestamp())
    jr = [x for x in reds if x["slug"] == JAN31][0]
    print("  January Contract redemption at %s = %s" % (utc(jr["ts"]), et(jr["ts"])))
    print("  after the 4:21 AM ET announcement (indictment para 13, complaint para 32): %s" % hms(jr["ts"] - ann))
    print("  after the 7:14 AM ET resolution (complaint para 33): %s" % hms(jr["ts"] - res))
    print("  sells executed %s to %s" % (et(sells[0]["ts"]), et(sells[-1]["ts"])))
    check("sells fall on Jan 3 ET (complaint para 56, indictment para 15)", all(et(x["ts"]).startswith("2026-01-03") for x in sells))
    r16 = 437859 * 10 ** 6
    r59 = 444209 * 10 ** 6
    print("  indictment para 16 vault transfer 437,859 vs redemptions %s: difference %s" % (usd(red_total), usd(red_total - r16)))
    print("  indictment para 16 / complaint para 59 444,209 vs proceeds %s: difference %s" % (usd(proceeds), usd(r59 - proceeds)))

    # ------------------------------------------------------------ 7. OrderFilled attribution
    print("\n7. OrderFilled attribution (fills_vandyke_txs.jsonl)")
    EX = "CTFExchange"

    def tok(t):
        return tmap.get(str(t))

    def shares_of(r):
        return r["ti"] if str(r["ma"]) == "0" else r["mi"]

    print("  rows %s, transactions %d, emitter %s, blocks %d to %d" % (
        "{:,}".format(len(fills)), len({r["tx"] for r in fills}), sorted({r["em"] for r in fills}),
        min(r["b"] for r in fills), max(r["b"] for r in fills)))
    pre = [r["b"] for r in fills if r["b"] < 80966779]
    print("  rows before block 80,966,779 (Dec 30 00:00:01Z): %d; earliest row block %d, %d blocks after the Dec 26 00:00:01Z anchor block 80,793,979" % (
        len(pre), min(pre), min(pre) - 80793979))
    print("  distinct outcome tokens in the slice: %d of %d in token_map.json" % (
        len({str(r["ma"]) for r in fills if str(r["ma"]) != "0"} | {str(r["ta"]) for r in fills if str(r["ta"]) != "0"}), len(tmap)))
    check("every row emitted by the CTF Exchange", all(r["em"] == EX for r in fills))
    check("every row has a USDC.e side and a mapped outcome token side",
          all((str(r["ma"]) == "0") != (str(r["ta"]) == "0") and tok(r["ma"] if str(r["ta"]) == "0" else r["ta"]) for r in fills))
    bytx = defaultdict(list)
    for r in fills:
        bytx[r["tx"]].append(r)

    def emission_check(wallets):
        nrows = okrows = ntx = oktx = 0
        for w in wallets:
            for tx, rs in bytx.items():
                cp = [r for r in rs if r["tk"] == w]
                if not cp:
                    continue
                own = [r for r in rs if r["mk"] == w and r["tk"] == EX]
                nrows += len(cp)
                ntx += 1
                if len(own) == 1:
                    okrows += len(cp)
                    if sum(shares_of(r) for r in cp) == shares_of(own[0]):
                        oktx += 1
        return nrows, okrows, ntx, oktx

    for name, ws in (("the named wallet", [W]),):
        n, ok, t, okt = emission_check(ws)
        print("  %s: %s of %s rows with taker == wallet sit in a transaction with exactly one own row (maker == wallet, taker == exchange); "
              "shares conserved in %d of %d transactions" % (name, "{:,}".format(ok), "{:,}".format(n), okt, t))
        check("emission rule, %s" % name, n == ok and t == okt)

    # maker frame reproduces the receipts
    mk_cash = defaultdict(lambda: [0, 0])
    for r in fills:
        if r["mk"] == W:
            if str(r["ma"]) == "0":
                mk_cash[r["tx"]][0] += r["mi"]
            else:
                mk_cash[r["tx"]][1] += r["ti"]
    trade = [x for x in rows if x["kind"] != "REDEEM"]
    match = sum(1 for x in trade if mk_cash[x["tx"]] == [x["out"], x["inn"]])
    print("  maker frame (rows with maker == wallet) vs receipts: %d of %d trade transactions match to the micro USDC.e" % (match, len(trade)))
    check("maker frame reproduces all 15 receipts", match == 15)
    mk_j = sum(r["ti"] for r in fills if r["mk"] == W and str(r["ma"]) == "0" and (tok(r["ta"]) or {}).get("market_slug") == JAN31 and tok(r["ta"])["outcome"] == "Yes")
    print("  maker frame January Contract Yes bought: %s shares (activity API %s)" % ("{:,.6f}".format(mk_j / 1e6), "{:,.6f}".format(j_sh)))
    check("maker frame jan31 shares equal the activity API to 1 micro share", abs(mk_j / 1e6 - j_sh) < 2e-6)

    # naive taker frame misbooking for the named wallet
    acc = defaultdict(int)
    for r in fills:
        if r["tk"] != W:
            continue
        if str(r["ta"]) == "0":       # maker sells token ma for USDC: naive parser books the wallet as buyer
            o = tok(r["ma"])["outcome"]
            acc["buy_usd_" + o] += r["ti"]
            acc["buy_sh_" + o] += r["mi"]
        else:                          # maker buys token ta with USDC: naive parser books the wallet as seller
            o = tok(r["ta"])["outcome"]
            acc["sell_usd_" + o] += r["mi"]
            acc["sell_sh_" + o] += r["ti"]
    tot_buy = acc["buy_usd_Yes"] + acc["buy_usd_No"]
    tot_sell_usd = acc["sell_usd_Yes"] + acc["sell_usd_No"]
    print("  a parser that books taker-field rows to the wallet adds, for the named wallet:")
    print("    Yes buys %s USDC.e for %s shares" % (usd(acc["buy_usd_Yes"]), "{:,.2f}".format(acc["buy_sh_Yes"] / 1e6)))
    print("    No buys  %s USDC.e for %s shares" % (usd(acc["buy_usd_No"]), "{:,.2f}".format(acc["buy_sh_No"] / 1e6)))
    print("    total buys %s USDC.e" % usd(tot_buy))
    print("    sale receipts %s USDC.e (counterparties buying No %s, buying Yes %s)" % (usd(tot_sell_usd), usd(acc["sell_usd_No"]), usd(acc["sell_usd_Yes"])))
    print("    misbooked buys as a share of the real buys: %.0f percent" % (100.0 * tot_buy / buy_total))
    print("    Yes sells %s shares, No sells %s shares" % ("{:,.2f}".format(acc["sell_sh_Yes"] / 1e6), "{:,.2f}".format(acc["sell_sh_No"] / 1e6)))
    check("misbooked buys total 16,699.75", usd(tot_buy) == "16,699.75")

    # worked example 1: 0x845d5e6b
    r845 = [r for r in rec15 if r["transactionHash"].startswith("0x845d5e6b")][0]
    _, _, tr = usdc_flows(r845)
    print("  tx %s USDC.e transfers:" % r845["transactionHash"])
    for frm, to, amt in tr:
        print("    %-18s -> %-18s %s" % ("wallet" if frm == W else frm, "wallet" if to == W else to, usd(amt)))
    splits = [who(lg["topics"][1]) for lg in r845["logs"] if lg["topics"][0] == POSITION_SPLIT]
    print("    PositionSplit stakeholder: %s; transaction sender: %s" % (sorted(set(splits)), r845["from"]))
    cp = [t for t in tr if t[1] == EX and t[0] != W]
    check("0x845d5e6b: counterparty pays 80,500.00, wallet pays 7,000.00, exchange forwards 87,500.00 to ConditionalTokens",
          [usd(t[2]) for t in cp] == ["80,500.00"] and any(f == W and t == EX and usd(a) == "7,000.00" for f, t, a in tr)
          and any(f == EX and t == "ConditionalTokens" and usd(a) == "87,500.00" for f, t, a in tr)
          and set(splits) == {EX} and r845["from"] != W)
    tk845 = [r for r in bytx[r845["transactionHash"]] if r["tk"] == W]
    print("    naive taker-frame rows in this tx: %d, all %s" % (len(tk845), sorted({tok(r["ta"] if str(r["ma"]) == "0" else r["ma"])["outcome"] for r in tk845})))

    # worked example 2: 0xde1f1ed8
    tde = [t for t in bytx if t.startswith("0xde1f1ed8")][0]
    legs = [r for r in bytx[tde] if r["tk"] == W and str(r["ta"]) == "0" and tok(r["ma"])["outcome"] == "No"]
    px = [r["ti"] / r["mi"] for r in legs]
    usd_l = sum(r["ti"] for r in legs)
    sh_l = sum(r["mi"] for r in legs)
    print("  tx %s: %d No legs, %s USDC.e over %s shares, implied %.4f, legs %.3f to %.3f" % (
        tde, len(legs), usd(usd_l), "{:,.2f}".format(sh_l / 1e6), usd_l / sh_l, min(px), max(px)))
    direct = [r for r in bytx[tde] if r["tk"] == W and str(r["ma"]) == "0" and tok(r["ta"])["outcome"] == "Yes"]
    print("    the other %s Yes went to %d Yes buyers directly" % ("{:,.2f}".format(sum(r["ti"] for r in direct) / 1e6), len(direct)))
    print("    the wallet's own activity row for this tx: SELL %s Yes for %s" % ("{:,.2f}".format(act_by_tx[tde]["size"]), usd(round(act_by_tx[tde]["usdcSize"] * 1e6))))
    yes_px = act_by_tx[tde]["price"]
    print("    Yes sold at %.4f; 1 minus that is %.4f" % (yes_px, 1 - yes_px))
    check("0xde1f1ed8: 17 No legs, 9,954.79 over 11,976.19 shares, 0.765 to 0.838",
          len(legs) == 17 and usd(usd_l) == "9,954.79" and "{:,.2f}".format(sh_l / 1e6) == "11,976.19"
          and "%.3f" % min(px) == "0.765" and "%.3f" % max(px) == "0.838")

    # ------------------------------------------------------------ 8. CSV output
    if args.out:
        os.makedirs(args.out, exist_ok=True)
        para = {1: "ind 11(a)", 2: "ind 11(b); compl 50", 3: "ind 11(b); compl 50", 4: "ind 11(c)", 5: "ind 11(c)",
                6: "ind 11(c); compl 50", 7: "ind 11(d)", 8: "ind 11(d); compl 50", 9: "ind 11(d)", 10: "ind 11(d); compl 50",
                11: "ind 11(d)", 12: "ind 11(d); compl 50", 13: "ind 11(d); compl 50", 14: "compl 53; ind 15",
                15: "compl 56; ind 15", 16: "compl 56; ind 15", 17: "compl 56; ind 15"}
        with open(os.path.join(args.out, "receipts_summary.csv"), "w", newline="") as f:
            wr = csv.writer(f, lineterminator="\n")
            wr.writerow(["n", "tx_hash", "block", "utc", "et", "type", "market_slug", "outcome", "shares_activity_api",
                         "usdc_e_out_receipt", "usdc_e_in_receipt", "source_paragraph"])
            for x in rows:
                if x["kind"] == "REDEEM":
                    continue
                wr.writerow([x["n"], x["tx"], x["block"], utc(x["ts"]), et(x["ts"]), x["kind"], x["slug"], x["outcome"],
                             "%.6f" % x["shares"], usd6(x["out"]), usd6(x["inn"]), para[x["n"]]])
        with open(os.path.join(args.out, "redemptions.csv"), "w", newline="") as f:
            wr = csv.writer(f, lineterminator="\n")
            wr.writerow(["n", "tx_hash", "block", "utc", "et", "market_slug", "outcome", "shares_activity_api", "usdc_e_in_receipt", "source_paragraph"])
            for x in reds:
                wr.writerow([x["n"], x["tx"], x["block"], utc(x["ts"]), et(x["ts"]), x["slug"], x["outcome"],
                             "%.6f" % x["shares"], usd6(x["inn"]), para[x["n"]]])
        with open(os.path.join(args.out, "funding_ladder.csv"), "w", newline="") as f:
            wr = csv.writer(f, lineterminator="\n")
            wr.writerow(["group_et", "transactions", "times_et", "shares_activity_api", "usdc_e_out_receipt", "cumulative_shares", "complaint_para_50"])
            for l in ladder:
                wr.writerow([l["group"], l["n"], l["times"], "%.6f" % l["shares"], usd6(l["usdc"]), "%.6f" % l["cum"], l["para50"]])
        cols = ["k", "b", "tx", "li", "oh", "mk", "tk", "em", "ma", "ta", "mi", "ti", "f"]
        with open(os.path.join(args.out, "fills_vandyke_txs.csv"), "w", newline="") as f:
            wr = csv.writer(f, lineterminator="\n")
            wr.writerow(cols + ["maker_gives_market", "maker_gives_outcome", "maker_gets_market", "maker_gets_outcome"])
            for r in fills:
                g, t = tok(r["ma"]), tok(r["ta"])
                wr.writerow([str(r[c]) for c in cols] + [
                    g["market_slug"] if g else "USDC.e", g["outcome"] if g else "", t["market_slug"] if t else "USDC.e", t["outcome"] if t else ""])
        print("\nwrote 4 CSVs to %s" % args.out)

    print("\n%s: %d check(s) failed" % ("FAIL" if FAILS else "OK", len(FAILS)) if FAILS else "\nOK: all checks passed")
    for n in FAILS:
        print("  failed:", n)
    sys.exit(1 if FAILS else 0)


if __name__ == "__main__":
    main()
