# PR Ideas — Verifiable Intent Examples

Notes on potential example contributions to the `examples/` directory.

---

## Existing Examples Overview

| File | What it demonstrates |
|---|---|
| `autonomous_flow.py` | Complete end-to-end 3-layer purchase: Issuer→User→Agent, with constraint checking and split L3a/L3b |
| `immediate_flow.py` | 2-layer flow (user present, no agent delegation, no L3) |
| `network_validation.py` | Network-side validation pipeline in isolation: chain verification + constraint enforcement + COLLAPSED vs FOUR_PARTY deployment modes |
| `constraint_checking.py` | All 8 registered constraint types and PERMISSIVE vs STRICT strictness modes |
| `selective_disclosure.py` | SD privacy routing — how the same L2 credential produces different views for Merchant (checkout only) vs Network (payment only) |

---

## Coverage Gaps — Good PR Candidates

1. **`error_cases.py`** — Tampered credentials, expired tokens, wrong keys, broken `sd_hash` binding. The existing examples only show happy paths; error handling is critical for spec conformance.
2. **`key_binding.py`** — Deep-dive on KB-JWT: how `cnf.jwk` at each layer proves key possession, and what happens if you try to present with the wrong key.
3. **`multi_item_checkout.py`** — Multiple line items with mixed acceptable/unacceptable products, demonstrating `CheckoutLineItemsConstraint` more thoroughly.
4. **`budget_and_recurrence.py`** — The 3 time-based constraint types (`payment.budget`, `payment.recurrence`, `payment.agent_recurrence`) are listed in the spec but never exercised with real fulfillment data.
5. **`four_party_mode.py`** — `network_validation.py` mentions FOUR_PARTY mode but only shows COLLAPSED.

---

## Strongest PR Idea: Mock Payment Processor Flow

### Concept

A single-file example simulating a full Stripe-like payment flow using only Python's standard library. No Flask, no Next.js, no new dependencies.

**Full demo flow:**

1. Mastercard (mock issuer) → Issues L1 for Alice (card \*1234)
2. Alice (user wallet app) → Creates L2, delegates to agent with constraints
3. Agent → Browses mock merchant, selects product, creates checkout, creates L3a (payment) + L3b (checkout)
4. Mock merchant → Receives L3b, verifies checkout chain
5. Mock Stripe processor → Receives L1 + L2 + L3a → Verifies VI chain → Checks constraints → Returns "approved"
6. Agent → Confirms order with merchant

### Why No Flask or Next.js Is Needed

Python's stdlib `http.server.BaseHTTPRequestHandler` handles all socket/HTTP plumbing. Everything lives in one file:

```python
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading, json

class MockProcessorHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers["Content-Length"])
        body = json.loads(self.rfile.read(length))

        # Real VI verification
        chain_result = verify_chain(...)
        constraint_result = check_constraints(...)

        response = {"status": "approved", "transaction_id": body["l3a"][:16]}
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(response).encode())

    def log_message(self, *args):
        pass  # silence default request logs


def main():
    # Start server in background thread
    server = HTTPServer(("127.0.0.1", 0), MockProcessorHandler)
    port = server.server_address[1]  # OS-assigned port, avoids port conflicts in CI
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()

    # Agent POSTs to it like a real processor
    import urllib.request
    payload = json.dumps({"l1": l1_ser, "l2": l2_payment_ser, "l3a": l3a_ser}).encode()
    req = urllib.request.Request(f"http://127.0.0.1:{port}/api/pay", data=payload)
    result = json.loads(urllib.request.urlopen(req).read())

    print(result)  # {"status": "approved", ...}
    server.shutdown()
```

`urllib.request` is also stdlib — no `requests` library needed. Runs as `python examples/mock_processor_flow.py`. One process, one file.

### Design Notes

- **Single file**: `MockProcessorHandler` class at the top, agent flow below. Readers see processor logic and agent logic side by side.
- **OS-assigned port**: Use `port=0` so the OS picks a free port — avoids flaky CI failures.
- **Avoid redundancy**: Merchant-side L3b verification is already in `autonomous_flow.py`. This example focuses on the processor side and references that file for the merchant checkout path.
- **Key detail**: The agent must build the selective L2 (payment disclosures only) with `build_selective_presentation()` before POSTing — easy to accidentally send the full L2.

### Why This Is a Strong Contribution

- Stays on-spec — VI is designed for card rails; this shows it doing exactly what it was built for
- Verification code already exists — building the integration layer, not reinventing constraint checking
- Relevant to Mastercard — shows their credential format working end-to-end with a payment processor
- No new dependencies — stays within the project's single-dep (`cryptography>=42.0`) constraint
