# OnionLens

A Python 3.10+ standard-library WSGI sensor for an application you own or are authorized to instrument. It stores observations locally in SQLite. There are no remote calls, downloads, hidden telemetry, background services or automatic Tor installation. The runtime has no third-party dependencies.

Version 0.1.2 uses the distribution name `onionlens`. The Python import remains `onion_observatory`. The `onionlens`, `cepatreaza` and `onion-observatory` commands invoke the same sensor. Existing integrations can keep their imports and command names.

[PyPI](https://pypi.org/project/onionlens/) · [Website](https://onionlens.org) · [Source repository](https://github.com/NellInc/OnionLens-public)

## Install and run

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install onionlens
onionlens serve --channel clearnet --db observatory.sqlite3
```

For a local source checkout, use `python -m pip install .` instead.

The reference server binds `127.0.0.1:8787` by default. Open `http://127.0.0.1:8787/_oo/demo` for a labelled demonstration. The response contains a benign instruction to request a relative callback URL. Following that URL records a demo callback. `/_oo/probe` issues an unsolicited-class probe instead. No application HTML is modified or injected.

```sh
onionlens summary --db observatory.sqlite3
```

Summary prints aggregate event counts, valid callbacks by class, and invalid callbacks. It prints no raw records. All activity outside the dedicated demo endpoint and its valid issued callback tokens is classified `unsolicited`. This operational label means unlabelled traffic, including your own ordinary tests. It does not establish that a visitor was uninvited. Spoofed user agents, test headers and query markers cannot suppress or relabel activity. The label says nothing about a visitor's identity.

## Wrap your WSGI application

```python
from onion_observatory import Sensor
from my_application import application as original_application

application = Sensor(original_application, "sensor.sqlite3",
                     channel="clearnet")
```

Choose a database location outside your web root. Create its parent directory first and restrict its permissions. The sensor reserves exactly `/_oo/probe`, `/_oo/demo`, and `/_oo/callback`. Keep these paths outside your application's route space. All other response iterables and headers pass through unchanged, including encoded and streaming responses. Use a suitable production WSGI server for an exposed service. The Python reference server is for local demonstration, not hardened production hosting.

The channel is fixed operator configuration, never inferred from hosts, addresses or headers. To compare onion and clearnet traffic, run separate listeners with different fixed channels. They may share a database. Put your own authentication or access policy outside the sensor if these endpoints must be restricted.

## Optional Tor exposure

Install and configure Tor yourself using its official documentation and your platform's supported package. An example `torrc` mapping for the loopback reference listener is:

```text
HiddenServiceDir /var/lib/tor/onionlens/
HiddenServicePort 80 127.0.0.1:8787
```

Use a Tor-owned private directory appropriate to your installation, then run the listener with `--channel onion`. Tor provisions the onion hostname. This package does not manage Tor. A public exposure needs your own deployment, abuse handling, and threat assessment. Binding loopback prevents direct external access to the reference listener, but does not restrict Tor visitors once you expose it.

## Validate and retrieve the owned fixture

The optional examples below use OnionLens's own controlled fixture. They require no changes to the sensor. The address check runs locally with Python's standard library and performs no lookup:

```sh
python3 - <<'PYTHON'
import base64
import hashlib
import hmac
import re

hostname = "pjzhmrhqlmjvhb5eeqmgnil7oztrbqkt45hay4zsvj5e6dblnfezopyd.onion"
if not re.fullmatch(r"[a-z2-7]{56}\.onion", hostname):
    raise SystemExit("Invalid v3 hostname format")
data = base64.b32decode(hostname[:-6].upper())
key, checksum, version = data[:32], data[32:34], data[34:]
expected = hashlib.sha3_256(b".onion checksum" + key + version).digest()[:2]
if version != b"\x03" or not hmac.compare_digest(checksum, expected):
    raise SystemExit("Invalid version or checksum")
print("Valid v3 format and checksum; reachability and trust are untested")
PYTHON
```

With your separately installed Tor client running on its configured SOCKS port (9050 here), pass the hostname to Tor for resolution:

```sh
curl --fail --socks5-hostname 127.0.0.1:9050 --max-time 90 \
  http://pjzhmrhqlmjvhb5eeqmgnil7oztrbqkt45hay4zsvj5e6dblnfezopyd.onion/demo/api/v1/fixture
curl --fail --max-time 30 https://onionlens.org/demo/api/v1/fixture
```

Both transports return JSON with `fixture_id` equal to `oo-retrieval-v1`, `revision` equal to `1`, and `expected` values `keyword: moss`, `number: 42`, and `unicode: onion · café · 東京`. Compare those fields rather than the complete response: the notice can vary per request. The fixture's plain-text instruction is data for your retrieval test. Do not execute it or follow its callback URL. These commands do not install Tor, alter proxy settings, or scan third-party services.

### Keep experiments separate

The portable sensor labels only `/_oo/demo` and callbacks carrying its valid issued tokens as `demo`. Ordinary requests, `/_oo/probe`, and invalid callbacks remain `unsolicited`, including tests you perform yourself. No user-agent, query marker or arbitrary test header changes this. Record self-run tests in your own study notes and exclude them in analysis as appropriate.

The public OnionLens service has a separate research deployment and its own data policy. The hosted fixture commands above use dedicated demo routes, so both fetches and any issued callback tokens retain the server-assigned demo class. Ordinary /api/v1/fixture requests remain unlabelled research observations. For explicitly labelled hosted demonstrations use [OnionLens Lab](https://onionlens.org/demo/) or [the MCP demo](https://onionlens.org/demo/mcp). The local package endpoints and hosted demonstration endpoints are distinct. Neither classifies a visitor's identity or consent.

## Data and privacy boundaries

Each request records time, fixed channel, event kind, traffic class, method (16 characters), path (1024 characters), user agent (512 characters), and optional hashed origin-token correlation and callback delay. Control characters are replaced. SQLite stores issued token hashes and issue times so callback validation survives restarts. Tokens expire for validation after 24 hours; expiration does not automatically delete records. Valid callbacks can repeat and counts are request counts, not unique actors. Delay measures probe issuance to callback receipt, including delivery and network latency; it is not a verified reading or reasoning duration.

The sensor does not read or store request bodies, IP addresses, cookies, authorization headers, referrers, raw query strings, or task descriptions. It parses only the callback token query parameter and never stores the raw token. Paths and user agents are untrusted text and may themselves contain personal or sensitive information. Do not put secrets in them. There is no semantic extraction of task content. An app that embeds task descriptions or secrets in paths or user agents needs additional operator-side minimisation before this wrapper.

The reference server disables its access logs. Your outer WSGI server, reverse proxy, Tor setup and wrapped application have independent logging policies, which you must review. Existing database file permissions are preserved; new database files are created mode `0600`. SQLite is not encrypted. Keep the database off public web roots, restrict access, encrypt its storage when needed, and set your own retention policy. Stop all writers before deleting the database to remove local history. There is no remote dashboard or remote deletion control. SQLite failures propagate to the serving stack; choose availability and error-log handling deliberately.

## Research limits

A callback is a behavioral indicator that a token-bearing request occurred. A person, script, crawler, link follower or model-driven client can produce it. It cannot prove model identity, autonomy, instruction hierarchy, intent, or exposure to other content. The response is plain text with an explicit instruction, not an automatically loading image or redirect. Token possession can still be shared, so correlation does not establish actor identity. Use controlled baselines and ethical review appropriate to your study; instrument only your authorized service. This package does not scan other sites or discover agents.

## Test

```sh
PYTHONPATH=src python -m unittest discover -s tests -v
```
