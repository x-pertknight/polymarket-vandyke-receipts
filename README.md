# Van Dyke Polymarket case reconciled to on-chain USDC.e receipts

Charts: https://x-pertknight.github.io/polymarket-vandyke-receipts/

This repository reconciles the trading figures in CFTC v. Van Dyke, No. 1:26-cv-03369 (CFTC Release 9217-26), and United States v. Van Dyke, S.D.N.Y. 26 Cr. 156, to the Polygon transaction receipts of the wallet described in those documents. Every share and USDC.e figure below is recomputed offline from the files in `code/raw/` by `code/recompute.py`.

Wallet `0x31a56e9e690c621ed21de08cb559e9524cdb8ed9` was identified from the masked address in complaint para 48 and para 57 and from the match between its activity and the figures in both documents. It was not found by a detection method. The link between the wallet and the defendant is the complaint's allegation. Van Dyke has pleaded not guilty and the charges have not been tried. No finding is made about any other wallet.

Share counts come from Polymarket's public activity API. Cash amounts come from USDC.e Transfer logs in the on-chain receipts. The API's USDC amounts match the receipts to 1 micro USDC.e on all 17 rows. The API returns 17 rows for the wallet, consistent with Compl. 57, which says the wallet was used for no other trading on Polymarket. Times are US Eastern (EST, UTC minus 5). Ind. is the indictment and Compl. is the complaint.

| # | Time ET | Tx | Type | Market (Jan 31 contracts) | Shares | USDC.e | Document | Source |
|---|---|---|---|---|---:|---:|---|---|
| 1 | Dec 27 00:05 | 0x6c6ceeb5 | Buy | US forces in Venezuela | 634.08 | 96.00 | approx. 634 shares, approx. $96 | Ind. 11(a) |
| 2 | Dec 30 19:20 | 0x29b392d7 | Buy | Maduro out | 13,769.33 | 1,238.34 | approx. 13,769 shares, approx. $1,238 | Ind. 11(b) |
| 3 | Dec 30 22:02 | 0x2c981ebe | Buy | Maduro out | 850.00 | 85.00 | approx. 850 shares, approx. $85 | Ind. 11(b) |
| 4 | Jan 1 18:55 | 0x91ef2b79 | Buy | US invades Venezuela | 17,857.89 | 1,000.00 | approx. 17,858 shares | Ind. 11(c) |
| 5 | Jan 1 18:56 | 0xdcc07448 | Buy | War Powers | 1,752.95 | 100.00 | approx. 1,752 shares | Ind. 11(c) |
| 6 | Jan 1 18:57 | 0xd863bd18 | Buy | Maduro out | 73,685.38 | 5,000.00 | approx. 73,685 shares; rows 4 to 6 approx. $6,100 | Ind. 11(c) |
| 7 | Jan 2 02:18 | 0x29d685a6 | Buy | War Powers | 2,533.13 | 100.00 | rows 7 and 9 approx. 3,618 shares | Ind. 11(d) |
| 8 | Jan 2 11:49 | 0x5b78b583 | Buy | Maduro out | 90,347.29 | 6,000.00 | approx. 90,347 shares | Ind. 11(d) |
| 9 | Jan 2 11:52 | 0xe808fab9 | Buy | War Powers | 1,085.60 | 50.00 | rows 7 to 9 approx. $6,150 | Ind. 11(d) |
| 10 | Jan 2 20:38 | 0x95547a71 | Buy | Maduro out | 82,420.83 | 6,000.00 | approx. 82,421 shares, approx. $6,000 | Ind. 11(d) |
| 11 | Jan 2 21:14 | 0x0426e790 | Buy | US forces in Venezuela | 563.70 | 50.00 | approx. 564 shares | Ind. 11(d) |
| 12 | Jan 2 21:15 | 0x845d5e6b | Buy | Maduro out | 87,500.00 | 7,000.00 | 87,500 shares; rows 11 and 12 approx. $7,050 | Ind. 11(d) |
| 13 | Jan 2 21:58 | 0x78d0e84d | Buy | Maduro out | 88,186.77 | 7,215.00 | approx. 88,187 shares, approx. $7,215 | Ind. 11(d) |
| 14 | Jan 3 08:41 | 0x4c8262f0 | Redeem | Maduro out | 436,759.61 | 436,759.61 | received more than approx. 436,000 USDC.e | Compl. 53 |
| 15 | Jan 3 15:25 | 0x86d5bc68 | Redeem | US forces in Venezuela | 1,197.77 | 1,197.77 | held until it resolved Yes | Compl. 56 |
| 16 | Jan 3 19:02 | 0xde1f1ed8 | Sell | US invades Venezuela | 17,857.88 | 3,143.26 | sold on Jan 3 before it resolved No | Compl. 56; Ind. 15 |
| 17 | Jan 3 19:03 | 0xef8cb973 | Sell | War Powers | 5,371.68 | 2,714.64 | sold on Jan 3 at a profit | Compl. 56; Ind. 15 |

Row 7 executed at 02:18 ET. Ind. 11(d) groups it with the morning of Jan 2.

## Totals

- Buys. 13 transactions, 33,934.34 USDC.e. Ind. 10 gives approximately $33,934. Ind. 11 gives 13 separate occasions.
- Maduro out by January 31, the complaint's January Contract. 7 buys, 436,759.61 shares for 32,538.34 USDC.e, average 0.07450. Compl. 52 gives more than 436,000 shares at approximately $0.074 for approximately $32,538.
- Proceeds. Redemptions 437,957.39 (Compl. 53, 56) plus sales 5,857.90 (Compl. 56, Ind. 15) equal 443,815.29 USDC.e.
- Net. 443,815.29 minus 33,934.34 equals 409,880.95. Ind. 15 gives approximately $409,881.
- January Contract only. 436,759.61 minus 32,538.34 equals 404,221.27. Compl. 53 gives more than $404,000.
- The other three contracts net 5,659.68. Compl. 55 gives more than $5,000.
- The January Contract redemption came 4h20m49s after the announcement at approximately 4:21 AM ET (Ind. 13, Compl. 32) and 1h27m49s after the resolution at approximately 7:14 AM ET (Compl. 33).

## Funding ladder, January Contract (Compl. 50)

| Period ET | Transactions | Times ET | Shares | Cumulative | Compl. 50 |
|---|---:|---|---:|---:|---|
| Dec 30 evening | 2 | 19:20, 22:02 | 14,619.33 | 14,619.33 | approx. 14,600 shares in two transactions |
| Jan 1 evening | 1 | 18:57 | 73,685.38 | 88,304.71 | 73,700 shares |
| Jan 2 morning | 1 | 11:49 | 90,347.29 | 178,652.01 | approx. 90,300 shares |
| Jan 2 evening | 3 | 20:38, 21:15, 21:58 | 258,107.61 | 436,759.61 | more than 250,000 shares in three transactions between 8:30 and 10:00 PM ET |

Shares are summed before rounding, so a period total can differ by 0.01 from the sum of the rounded rows above.

## Two residuals

- Ind. 16 says approximately 437,859 USDC.e went to a vault on Jan 3. The redemptions total 437,957.39. The difference is 98.39.
- Ind. 16 and Compl. 59 give 444,209 for a later transfer. Proceeds here are 443,815.29. The difference is 393.71.

Both figures describe the withdrawal from the wallet and later transfers. Those transactions are not among the receipts used here, so this data cannot explain the differences. They are not rounding.

## Reproduce

```
python3 -I code/recompute.py
cd data && shasum -a 256 -c SHA256SUMS
```

`recompute.py` uses the Python standard library only and makes no network calls. `code/fetch/` holds the network steps that regenerate the raw files. `NOTE-orderfilled-attribution.md` explains how the exchange's fill events must be attributed. `VERIFICATION.md` lists what was checked and what changed from the earlier submission.

## Check another wallet (original exchange contracts only)

`code/check_wallet.py` applies the maker rule from the note to any wallet and prints the real buys and sales next to the naive count that also books the wallet's counterparty rows.

```
python3 -I code/check_wallet.py 0x31a56e9e690c621ed21de08cb559e9524cdb8ed9 --jsonl code/raw/fills_vandyke_txs.jsonl
python3 -I code/check_wallet.py WALLET --csv orderfilled_export.csv
python3 -I code/check_wallet.py WALLET --rpc RPC_URL --from-block START --to-block END --chunk 50
```

On the shipped slice it prints real buys 33,934.34 against a naive 50,634.09, and real sales 5,857.90 against a naive 353,723.55. In the shipped slice only the named wallet is unredacted, so other wallets need the CSV or RPC input.

The CSV input takes OrderFilled rows with the columns maker, taker, makerAssetId, takerAssetId, makerAmountFilled, takerAmountFilled and evt_tx_hash or transactionHash, plus fee and evt_index when present. The RPC input needs an endpoint that serves archive eth_getLogs. Free public endpoints cap the block range per call, hence the small chunk.

Scope and limits. The script reads the original CTF Exchange and NegRisk CTF Exchange contracts with USDC.e collateral. Polymarket now trades on newer exchange contracts that it does not read, so it covers fills up to that migration. It reports exchange fills only. Redemptions, splits, merges, neg risk conversions and token transfers are not counted, so the sales figure is not the wallet's cash out. Amounts are gross of fees and the fee total is printed separately. The neg risk path is untested because the shipped slice has no neg risk rows. Pass the Polymarket proxy wallet that appears in the maker field, not the signing EOA. A wallet with no rows prints a warning. The 49 percent and 60x multiples come from this wallet's trades and are not a general error rate.
