# Attributing OrderFilled rows on the Polymarket CTF Exchange

This note describes documented exchange behaviour. Polymarket's documentation and public analyses already describe it, and several trade data vendors already label the two kinds of row. It is written as a checklist item for a compliance desk that parses fills itself. It is not a discovery.

## How the exchange emits fills

One trade is one `matchOrders` call with one taker order and one or more maker orders. The CTF Exchange emits one `OrderFilled` per order. Each maker order gets a row whose maker field is the maker and whose taker field is the owner of the taker order. The taker order gets one more row whose maker field is the taker and whose taker field is the exchange. That last row is the taker's whole fill.

In a mint match the taker buys Yes and the makers buy No. The exchange takes USDC.e from both sides and splits it into Yes and No. In a merge match the taker sells Yes and the makers sell No, and the exchange merges the pair back into USDC.e. So the maker rows in these matches carry the complementary token. Markets on the neg risk exchange follow the same pattern with that exchange in the taker field. All 268 rows in the shipped slice come from the CTF Exchange.

A parser that credits every row naming a wallet in the taker field to that wallet misbooks the makers' fills as the wallet's trades. Rows that point the same way as the wallet's own trade count it twice. Rows that carry the complementary token book a trade the wallet never made.

## Two worked examples from the named wallet

Tx `0x845d5e6b` (Jan 2, 21:15 ET). The wallet buys 87,500.00 Yes for 7,000.00 USDC.e. One maker order buys 87,500.00 No for 80,500.00 USDC.e. The receipt shows the counterparty paying 80,500.00 and the wallet paying 7,000.00 to the exchange. The exchange forwards 87,500.00 to the ConditionalTokens contract to split. The PositionSplit stakeholder is the exchange, and the transaction sender is a third address. A taker field parser books the wallet as selling 87,500.00 No for 80,500.00. That cash never reached the wallet.

Tx `0xde1f1ed8` (Jan 3, 19:02 ET). The wallet sells 17,857.88 Yes for 3,143.26 USDC.e, at 0.1760 per share. Seventeen maker orders sell No into the merge. They receive 9,954.79 USDC.e for 11,976.19 No, at 0.765 to 0.838 per share, 0.8312 on average. The other 5,881.69 Yes went to 14 Yes buyers directly. A taker field parser books the wallet as buying the 11,976.19 No. The prices are correct complements of the Yes price (1 minus 0.1760 is 0.8240), so an implied price check does not flag the rows.

## Size of the error for the named wallet

Applied to every row in the shipped slice that names the wallet in the taker field, a taker field parser adds the following.

| Misbooked item | USDC.e | Shares |
|---|---:|---:|
| Yes buys | 6,080.06 | 88,573.68 |
| No buys | 10,619.69 | 13,370.95 |
| All buys | 16,699.75 | |
| Sale receipts | 347,865.64 | |
| Yes sells | | 9,858.61 |
| No sells | | 372,613.28 |

The wallet's real buys total 33,934.34 USDC.e (see README). The misbooked buys would inflate that by 49 percent. These rows are real fills by real counterparties. They are wrong only when booked to the wallet. Of the 347,865.64, 344,759.00 is cash that counterparties paid for No in the mint matches that filled the wallet's Yes orders.

## The rule

Attribute each `OrderFilled` row to its maker field. For a given wallet, use the rows where the wallet is the maker. Skip the rows where the wallet is in the taker field, because the wallet's own row (taker field equal to the exchange) already carries its whole fill.

The rule is decidable from the fills alone. It follows from the exchange contract, which gives the taker order its own row with the exchange in the taker field. The shipped slice confirms it for the named wallet. Every row with the wallet in the taker field sits in a transaction where the wallet has exactly one own row, and the shares on the counterparty rows sum exactly to the shares on that own row. This holds on 253 of 253 rows and 15 of 15 transactions. That is one wallet, so a parser should run the same check on its own data.

Receipts verify a parser. They are not a required ingredient of one. Here the maker rule reproduces all 15 trade receipts to the micro USDC.e and the 436,759.61 January Contract shares reported by the activity API.

## Checklist

- Does the parser drop or rekey rows whose taker field is an exchange contract?
- Does it credit rows to the maker field only?
- In mint and merge matches, does it keep the complementary token on the maker rows instead of booking it to the taker?

`python3 -I code/recompute.py` prints every figure in this note (section 7 of its output).

Sources: Polymarket documentation on exchange fills (https://docs.polymarket.com/resources/onchain-position-data). CTF Exchange contract source (https://github.com/Polymarket/ctf-exchange). Paradigm, Polymarket Volume Is Being Double-Counted, December 2025 (https://www.paradigm.xyz/writing/polymarket-volume-is-being-double-counted). Polynode trade event documentation (https://docs.polynode.dev/websocket/events/trade).
