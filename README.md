# bonfire-tools

Local dev tools for Bonfires: a proxy server, a knowledge graph explorer, an activity monitor and a document ingester. Python 3.10+, no dependencies.

## Configuration

Credentials come from environment variables only. Nothing secret is stored in this repo.

| Variable | Used by | Required |
| --- | --- | --- |
| `DELVE_API_KEY` | `ingest.py`, `server.py` | yes |
| `BONFIRE_ID` | `ingest.py`, `server.py` | yes |
| `DELVE_BASE_URL` | `ingest.py` | no (default `https://tnt-v2.api.bonfires.ai`) |

```bash
cp .env.example .env   # fill in your values; .env is git-ignored
set -a; source .env; set +a
```

Both scripts exit with an error if a required variable is missing (`ingest.py --dry-run` works without them).

## Usage

```bash
python3 ingest.py search "query string"
python3 ingest.py text "some content" --source "live-notes"
```

```bash
python3 server.py
# then open http://localhost:8888/pulse.html or http://localhost:8888/memory-explorer.html
```

`server.py` listens on localhost only. It adds `DELVE_API_KEY` to proxied `/api/*` requests and serves `BONFIRE_ID` to the pages at `/config.json`, so the HTML never contains the key. If you open the HTML pages some other way, they ask for the API key and bonfire ID once and keep them in that browser's `localStorage` (clear them with `localStorage.removeItem('bonfires_api_key')` and `localStorage.removeItem('bonfires_bonfire_id')`).
