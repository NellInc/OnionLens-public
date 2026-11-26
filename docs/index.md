# OnionLens

Read-only Tor tools and a lightweight Python sensor that shows when automated readers act on instructions embedded in a fetched document.

- [PyPI package](https://pypi.org/project/onionlens/)
- [Public source and tests](https://github.com/NellInc/OnionLens-public)
- [Installable wheel](https://onionlens.org/downloads/onionlens-0.1.4-py3-none-any.whl)
- [Source archive](https://onionlens.org/downloads/onionlens-0.1.4.zip)
- [Checksums](https://onionlens.org/downloads/SHA256SUMS.txt)
- [MCP integration](https://onionlens.org/docs/mcp.md)
- [Traffic separation and privacy](https://onionlens.org/docs/traffic.md)

## How it works in two steps

1. **Fetch:** When a client loads a page or tool response, the server includes a short text note with a fresh one-time token. Humans and normal browsers ignore it.
2. **Callback:** If an automated reader follows the note and sends that token back to the callback URL, the sensor links the callback to the fetch that created the token. That link shows a client read the response and acted on it, while who ran it, which AI model it really is, and why it visited remain unknown.

## Install the portable sensor

Requires Python 3.10 or newer. Install [OnionLens from PyPI](https://pypi.org/project/onionlens/) in a virtual environment.

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install onionlens
onionlens serve --channel clearnet --db observatory.sqlite3
```

For an offline install, download the wheel, compare its SHA256 with the checksum file, then run `python -m pip install onionlens-0.1.4-py3-none-any.whl` from its folder.

Open http://127.0.0.1:8787/_oo/demo to try a labelled local experiment in your browser. The package uses only the Python standard library at runtime, sends zero outside telemetry, and never installs or reconfigures Tor. Its built-in server is for local evaluation; wrap your WSGI app for production. Existing `onion_observatory` imports and `cepatreaza`/`onion-observatory` commands continue to work.

## Test retrieval over both transports

When testing your own Tor client or AI agent, use the `/demo/` routes so your test requests are tagged as a demo from the start. Pass `--socks5-hostname` to `curl` so `curl` hands the raw `.onion` hostname to your local Tor SOCKS proxy (normal DNS servers cannot resolve `.onion` names).

```sh
curl --fail --max-time 30 https://onionlens.org/demo/api/v1/fixture
curl --fail --socks5-hostname 127.0.0.1:9050 --max-time 90 \
  http://pjzhmrhqlmjvhb5eeqmgnil7oztrbqkt45hay4zsvj5e6dblnfezopyd.onion/demo/api/v1/fixture
```

Check `fixture_id=oo-retrieval-v1`, `revision=1`, `expected.number=42` and `expected.unicode="onion · café · 東京"`. Compare only those fixed fields: the `notice` field changes on every fetch because it carries a fresh one-time canary token. Treat that notice as untrusted document text; your client does not need to follow it to use the tool.

The [address checker](https://onionlens.org/field/validate) unpacks any 56-character v3 `.onion` address into its 32-byte Ed25519 public key, two-byte SHA3-256 checksum, and one-byte version (`3`), and verifies the checksum locally without connecting to the address over the network. A valid checksum means there are no typos in the address; it says nothing about whether the service is online or trustworthy.
