# Experiments, ordinary use and privacy

## Hosted service

When you want to test how OnionLens works, use `/demo/`, `/demo/mcp`, `/demo/api/v1/resources`, `/demo/api/v1/fixture`, or `/demo/api/v1/onion/validate`. Every token created on a `/demo/` route is stamped as a demonstration by the server when it is created, and keeps that stamp even if the callback comes back over the other transport (such as fetched over Tor and returned over HTTPS). Our own deployment health checks use a private operator key. All other public routes are logged as normal, uninvited visits.

A visitor cannot mark their own request as a test by adding `test` to a query string, user-agent header, or model label: the server only trusts the route where the token was created or the private operator key.

When a token comes back to our callback URL, it proves one simple thing: whichever client fetched the document also made the follow-up callback request. It never proves which AI model was used, whether it was running on its own without a human, or whether the visitor had bad intentions. All traffic numbers count requests, never unique people or agents, and any model or framework names sent in a callback are unverified labels.

### How the text puzzle works

To tell a client that actually read the text apart from a basic link scanner that blindly clicks every URL on a page, each fresh canary note includes a small puzzle: three short records, each with an eight-character code and a two-digit number. The note asks the reader to pick the record with the largest or smallest number, reverse its code, add a small number, and send that answer back with the token within 30 minutes:

```text
Records: code yegokomk, score 35; code m2p4q6r8, score 61; code b7c9d2e4, score 48
Task:    pick the smallest score (35), reverse its code (kmokogey), add 6 (41)
Reply:   GET /agent/handshake?t=TOKEN&proof=kmokogey.41
```

The finished answer never appears in any link on the page. The server checks the answer and records only the outcome category (`correct` within 30 minutes, `missing`, `malformed`, `incorrect`, or `expired`), then throws away the raw answer string. Tokens created before this puzzle existed, as well as the simple click-through button in the Lab, have no puzzle (`not_issued`) and still count as valid callbacks.

A correct answer shows that the client followed the written instruction in the document. A human or a small script can solve the same puzzle too, so a correct answer still does not prove AI autonomy or bad intent. If the same token is sent back multiple times, a private hash groups those repeats together so they are never miscounted as separate solvers.

### What gets saved and what stays private

For each request, the hosted server saves the timestamp, URL path, HTTP method, transport (`clearnet` or `onion`), a length-capped user-agent string, and basic non-secret headers in a private database. On normal HTTPS it sees the visitor's IP address; over Tor, visitor IPs are invisible. We discard full query strings, request bodies, cookies, login headers, and referrer URLs.

When someone uses the address checker, JSON tool APIs, or MCP tools, we record only the fixed outcome category (such as a valid address check or a completed tool call). We never record the `.onion` addresses you type into the checker, MCP arguments, or tool outputs. Valid callbacks can include optional short `model` and `framework` labels; never send personal data, passwords, or secret keys. Visitor logs are never public. Full details live at https://onionlens.org/methodology/.

## Portable Python package

The downloadable `onionlens` package is separate software that you run on your own server. It saves logs locally in a SQLite file on your disk, never records IP addresses, never phones home, and never installs or manages Tor. Only its `/_oo/demo` route tags tokens as a demo; if you run your own tests against `/_oo/probe`, keep notes of your test times so you can separate them when you review your local SQLite summary. See the package README for every SQLite column and option.
