# Experiments, ordinary use and privacy

## Hosted service

Use /demo/, /demo/mcp, /demo/api/v1/fixture and /demo/api/v1/onion/validate for deliberate experiments. The server assigns demo provenance from these dedicated routes; issued callback tokens retain that provenance across transports. Operator QA uses authenticated test issuance, without publishing an operator credential. Ordinary public routes remain instrumented.

User-agent names, query markers and claims of being a test never authorize exclusion from monitoring. A referral or campaign source is a separate acquisition attribute, not permission to relabel a visit. Invited benchmark runs are experiments; ordinary users choosing a published tool are genuine usage, without establishing autonomous discovery.

A valid canary callback correlates an action to an issued token. It does not establish a model's identity, autonomy or malicious intent. Counts are requests, not distinct people or agents. Self-reported model and framework labels are unverified.

The hosted deployment records bounded request metadata and token correlations in a private database. Clearnet ingress records an edge-observed IP; onion visitor IPs are unavailable. Full query strings and request bodies, cookies and authorization headers are not retained by this application. Valid canary callbacks can retain bounded self-reported model, framework and task descriptions from query or form fields. These are unverified visitor-supplied text and may contain sensitive material. Never supply personal data, credentials or secrets. Full visitor records are never public. See https://onionlens.org/methodology/ for the hosted collection policy and storage limitations.

## Portable package

The package is separate software. It stores observations locally in SQLite, sends no telemetry and never installs Tor. Only /_oo/demo and callbacks from its issued tokens are demo. Ordinary local tests outside those routes remain unlabelled; keep study notes and account for them in your analysis. The package does not implement the hosted operator authentication mechanism. See the public README for all recorded fields, token expiry and deployment boundaries.
