# Verification

## What was recomputed, and by what

`code/recompute.py` recomputes every number in `README.md` and `NOTE-orderfilled-attribution.md` from the six files in `code/raw/`. It uses the Python standard library only and makes no network calls. It exits with status 0 only if all of its checks pass. It was run as `python3 -I code/recompute.py` from a directory outside the repository, on Python 3.10 and 3.13, with the same output.

Cash figures come from USDC.e Transfer logs in the transaction receipts, kept at the full 6 decimals and rounded to the cent only for display. Share counts and trade sides come from Polymarket's public activity API. The script checks that the API's USDC amount equals the receipt amount on all 17 rows to 1 micro USDC.e. It also checks that `block_ts.json` agrees with the `blockTimestamp` field of every receipt.

The four CSVs in `data/` are written by `python3 -I code/recompute.py --out DIR`. They were regenerated into an empty directory and compared byte for byte with the committed files. `data/SHA256SUMS` pins the four CSVs (the fills slice uncompressed) and the six raw files.

On 2026-11-07 the earlier version was recomputed independently. That check wrote its own reducer over the same raw files instead of running the earlier pipeline.

## Inputs

| File | Content | Source |
|---|---|---|
| `receipts_15tx.json` | receipts of the 15 trade transactions | Polygon `eth_getTransactionReceipt` |
| `receipts_redeems.json` | receipts of the 2 redemptions | Polygon `eth_getTransactionReceipt` |
| `dataapi_activity.json` | the wallet's 17 activity rows | Polymarket Data API, `/activity` (v1 route, captured before Polymarket retired it) |
| `fills_vandyke_txs.jsonl` | 268 `OrderFilled` rows in 15 transactions | Polygon `eth_getLogs` scan |
| `token_map.json` | 32 outcome tokens of 16 markets | Polymarket Gamma API |
| `block_ts.json` | timestamps of 59 blocks | Polygon `eth_getBlockByNumber` and receipt logs |

The fills slice comes from a scan of blocks 80,793,979 to 81,312,371 (Dec 26 to Jan 7 UTC) for `OrderFilled` rows on the 32 tokens in `token_map.json`. It keeps every row of the 15 transactions in which the named wallet is maker or taker, which is 15 own rows and 253 counterparty rows. `code/fetch/redact.py` cuts it from the full scan. No finding is made about any other wallet.

## Redaction

Every 20-byte address in the shipped files is replaced by a label, except the named wallet. Public contracts become `USDC.e`, `CTFExchange`, `ConditionalTokens` and `POLToken`. Every other address becomes `anon-TT-NN`, where TT numbers the transaction and NN the address within it, both by first appearance. Labels are scoped to one transaction. Within a transaction the same address gets the same label in every file, so the files still join. Across transactions the same address gets different labels, so the files cannot be used to count how often any wallet traded with the named wallet without looking up the transaction hashes on chain. A maker does not choose who fills its resting order, so being a counterparty implies nothing about a wallet. Transaction hashes, order hashes and token IDs are unchanged, so any row can be checked against the chain. `code/fetch/redact.py` is the step that does this.

SHA-256 of the files before redaction, for anyone holding the originals.

| File | SHA-256 |
|---|---|
| `receipts_15tx.json` | `f00ad4bade5c3df7ab89e109214fb6aa419a32980780296f958fba96212fe7eb` |
| `receipts_redeems.json` | `d75079e6404a19bba04923f8435a4299e90a940fef2fb81faa3dfb7dd4d38fad` |
| `dataapi_activity.json` | `66dbd4eab850e75ef9bd026bcba7aba9677965344c08429a62c5d0e9b4921ee1` |
| `fills_vandyke_txs.jsonl` (as cut by `redact.py` from the scan) | `0c6c0b79b977279485328a4d679e7d16d8b2e04aa0374caad5a4ab02e10ef338` |
| `token_map.json` | `0ffd68cc4bad63fcc1f4b7979a543953d98645313bd99958434a0fea5e11a7c1` |
| `block_ts.json` (earlier version, 57 blocks) | `a8298ddd1b543c095cabd25e6a9b4cf88fa58ae306e339eeff063d36dc37eedd` |

`block_ts.json` was then changed in three ways. The two redemption blocks, 81,164,225 and 81,176,332, were added from the receipts' `blockTimestamp`. The `_et_boundaries` entry, which served the removed window comparison, was dropped. Two provenance strings that pointed to an unshipped file were reworded.

## Network steps

`code/fetch/` regenerates the raw files and writes to `code/fetch/out/`. Run `dataapi.py` (now on the v2 route, `/v2/activity`), then `redeem_receipts.py` (which now fetches the trade receipts as well as the redemptions), then `polymarket_fetch.py --meta`, `--blocks` and `--scan 80793979 81312371`, then `redact.py`. The scan writes the full `fills.jsonl`. `redact.py` cuts the slice from it before redacting, unless `out/fills_vandyke_txs.jsonl` already exists, so delete that file after a fresh scan. The scan takes about an hour on free public RPC endpoints. Public endpoints can change, and the activity API is live, so a rerun may differ from the shipped files. The receipts are fixed by their transaction hashes.

## Corrections versus the earlier submission

- CFTC window label. The earlier report called Dec 30 00:00Z to Jan 4 00:00Z the CFTC window. Neither document uses that window. Compl. 50 ends on Jan 2 near 10:00 PM ET, and Ind. 10 runs from Dec 27 to Jan 2 at 9:58 PM EST. All window comparisons are removed.
- 1.1108. This multiplier was withdrawn in the earlier report but still quoted in an earlier version. All multipliers are removed.
- Para 9 citation. Account creation is Compl. 48 and Ind. 10. Compl. 9 covers residence and employment.
- "Dec 26 to 29 excluded". This was false. The shipped slice holds 4 rows before block 80,966,779 (Dec 30 00:00:01Z), all from the wallet's Dec 27 buy at block 80,846,349.
- "Within rounding". The residuals of 98.39 and 393.71 are not rounding. They come from transfers after the funds left the wallet, which the receipts do not show.
- "Every dollar". Not every figure in the documents reproduces. The two residuals do not, and share counts come from the activity API, not from receipts.
- "7 markets". This counted markets inside a scan already filtered to one market family, so it described the scan, not a wallet. Removed with the other wallet findings.
- "No other activity in 12 days". This held only inside the 16 scanned markets. Removed with the other wallet findings.

Other changes. The behavioural heuristics, the ranking of other wallets, the window comparisons and every other wallet's address are gone. The word "phantom" is replaced by "misbooked", since those rows are real fills by real counterparties. The prescription to use receipts as the arbiter is replaced by the maker field rule, which the fills alone decide. The misbooking figure now includes the No side, 16,699.75 USDC.e of buys instead of 6,080.06. Tables that were typed constants are now computed. The gzip hash, which depended on the zlib build, is replaced by the hash of the uncompressed CSV.

## Changes on 2026-11-08

- The fills slice now holds only the 268 rows of the named wallet's 15 transactions. Every figure in the README is unchanged. The note's emission count now covers the named wallet only.
- Counterparty labels are scoped to one transaction (see Redaction).
- `redact.py` now includes the cut. Run by the author on the unredacted originals, it reproduced the shipped `fills_vandyke_txs.jsonl`, `receipts_15tx.json` and `receipts_redeems.json` byte for byte. A fresh scan or RPC response may differ in format, so readers can compare content, not bytes.
- `dataapi.py` reads the v2 activity route, since Polymarket retired v1 on 2 November 2026 (https://docs.polymarket.com/migrate/data-api-v1-to-v2), and writes the rows in the v1 field names. On 2026-11-08 it returned the same 17 rows as the shipped file, field for field.
- Two source links in the note that redirect were updated.

## Repository checks

- `python3 -I code/recompute.py` run from outside the repository. All checks pass, and every number in the README and the note matches its output and the cited paragraph.
- No U+2014 or U+2013 character in any file.
- No 20-byte address other than the named wallet in any data file, in bare, topic or data word form. The all-zero address appears as the mint and burn counterparty in token transfer logs. `code/check_wallet.py` holds the addresses of the two public exchange contracts it queries.
- `cd data && shasum -a 256 -c SHA256SUMS` passes.
