#!/usr/bin/env python3
"""Fetch on-chain receipts for every transaction in the wallet's Polymarket activity (network step).

Reads out/dataapi_activity.json (written by dataapi.py).
TRADE rows          -> out/receipts_15tx.json
REDEEM/CONVERT rows -> out/receipts_redeems.json
Adds every receipt block to out/block_ts.json (timestamp via eth_getBlockByNumber).
"""
import json, os, time, datetime, urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))
RAW = os.environ.get('FETCH_OUT') or os.path.join(BASE, 'out')
ENDPOINTS = ['https://polygon.drpc.org', 'https://polygon-bor-rpc.publicnode.com', 'https://polygon.1rpc.io']
HDR = {'User-Agent': 'curl/8.7.1', 'Content-Type': 'application/json'}

def rpc(method, params, tries=2):
    body = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params}).encode()
    last = None
    for _ in range(tries):
        for url in ENDPOINTS:
            try:
                req = urllib.request.Request(url, data=body, headers=HDR)
                with urllib.request.urlopen(req, timeout=25) as r:
                    d = json.loads(r.read().decode())
                if 'error' in d:
                    raise RuntimeError(str(d['error']))
                return d['result']
            except Exception as e:
                last = e
                time.sleep(1.0)
    raise RuntimeError('RPC %s failed: %s' % (method, last))

def utc(ts):
    return datetime.datetime.fromtimestamp(int(ts), datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

items = json.load(open(RAW + '/dataapi_activity.json'))


def fetch(rows, path):
    existing = json.load(open(path)) if os.path.exists(path) else []
    have = set(r.get('transactionHash') for r in existing)
    for i in rows:
        tx = i.get('transactionHash')
        if not tx or tx in have:
            continue
        r = rpc('eth_getTransactionReceipt', [tx])
        if not r:
            print('SKIP null receipt', tx)
            continue
        existing.append(r)
        have.add(tx)
        print('tx %s... blk %d status %s logs %d' % (tx[:14], int(r['blockNumber'], 16), r.get('status'), len(r.get('logs', []))))
        time.sleep(0.15)
    json.dump(existing, open(path, 'w'), indent=1)
    print('%s: %d receipts' % (os.path.basename(path), len(existing)))
    return existing

trades = [i for i in items if i.get('type') == 'TRADE']
reds = [i for i in items if i.get('type') in ('REDEEM', 'CONVERT')]
print('TRADE rows: %d, REDEEM/CONVERT rows: %d' % (len(trades), len(reds)))
existing = fetch(trades, RAW + '/receipts_15tx.json') + fetch(reds, RAW + '/receipts_redeems.json')

bts = json.load(open(RAW + '/block_ts.json')) if os.path.exists(RAW + '/block_ts.json') else {}
for r in existing:
    b = int(r['blockNumber'], 16)
    if str(b) not in bts:
        blk = rpc('eth_getBlockByNumber', ['0x%x' % b, False])
        ts = int(blk['timestamp'], 16)
        bts[str(b)] = {'ts': ts, 'utc': utc(ts), 'how': 'eth_getBlockByNumber'}
json.dump(bts, open(RAW + '/block_ts.json', 'w'), indent=1)
print('block_ts.json: %d numeric blocks' % len([k for k in bts if str(k).isdigit()]))
