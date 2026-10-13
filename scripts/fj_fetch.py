#!/usr/bin/env python3
"""Fetch the consolidated Laws of Fiji from the official laws.gov.fj JSON API.

Caches every API response under _raw/fj/api/ so re-runs don't re-download.
Usage: fj_fetch.py [RAW_DIR]
"""
import json, os, sys, time, hashlib, base64
from concurrent.futures import ThreadPoolExecutor
import requests

API = "https://www.laws.gov.fj/api"
UA = "LawCodex/1.0 (+https://github.com/LawCodex)"
RAW = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "../../_raw/fj")
CACHE = os.path.join(RAW, "api")
os.makedirs(CACHE, exist_ok=True)
S = requests.Session()
S.headers["User-Agent"] = UA


def get(endpoint, force=False):
    name = endpoint.replace("/", "__")
    if len(name) > 150:
        name = name[:100] + hashlib.md5(name.encode()).hexdigest()
    path = os.path.join(CACHE, name + ".json")
    if os.path.exists(path) and not force:
        with open(path) as f:
            return json.load(f)
    for attempt in range(6):
        try:
            r = S.get(f"{API}/{endpoint}", timeout=120)
            if r.status_code == 200:
                data = r.json()
                tmp = path + ".tmp"
                with open(tmp, "w") as f:
                    json.dump(data, f)
                os.replace(tmp, path)
                return data
            if r.status_code == 404:
                return None
            print("HTTP", r.status_code, endpoint, file=sys.stderr)
        except Exception as e:  # noqa
            print("ERR", endpoint, e, file=sys.stderr)
        time.sleep(2 ** attempt)
    raise RuntimeError("failed " + endpoint)


def nodes(tree):
    for x in tree:
        yield x
        yield from nodes(x.get("SectionData") or [])


def main():
    acts = get("get_all_acts", force=True)
    get("retrieve_constitution", force=True)
    print(len(acts), "acts")
    with ThreadPoolExecutor(3) as ex:
        tocs = list(ex.map(lambda a: get("get_act_by_id/" + a["ActId"]), acts))
    ids = []
    for toc in tocs:
        for grp in toc or []:
            for n in nodes(grp.get("Sections") or []):
                if n.get("LegalId"):
                    ids.append(n["LegalId"])
    ids = list(dict.fromkeys(ids))
    print(len(ids), "nodes")
    done = [0]

    def one(i):
        get("retrieve_html/" + i)
        done[0] += 1
        if done[0] % 1000 == 0:
            print(done[0], flush=True)

    with ThreadPoolExecutor(3) as ex:
        list(ex.map(one, ids))


if __name__ == "__main__":
    main()
