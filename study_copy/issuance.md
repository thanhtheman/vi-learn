
## Explanation of `src/verifiable_intent/issuance/`

> This answer explains the 5 issuance functions that build the 3-layer SD-JWT delegation chain in the Verifiable Intent project.

The `issuance/` module has 5 functions across 3 files that build the 3-layer SD-JWT delegation chain.

---

## `issuer.py` — Layer 1

**`create_layer1(credential, issuer_private_key)`**

The Credential Provider (e.g. Mastercard) mints the root credential. It:
- Takes an `IssuerCredential` model (holds user identity, PAN, etc.)
- Creates one selective disclosure: `email` (everything else — `iss`, `sub`, `cnf`, `pan_last_four`, `scheme` — is always visible)
- Returns a signed ES256 `sd+jwt`

The `cnf.jwk` in the payload is the user's public key — this is what binds the user to the credential and lets them sign L2.

---

## `user.py` — Layer 2 (two modes)

**`create_layer2_immediate(mandate, user_private_key)`**

Used when the user is present at checkout. Final values (cart, payment) are signed directly — no agent delegation. Both `final_checkout` and `final_payment` become individual disclosures, referenced by hash in `delegate_payload`. Returns a `kb-sd-jwt`.

**`create_layer2_autonomous(mandate, user_private_key)`**

Used for AI agent delegation. More complex — a 5-step build:
1. Creates standalone disclosures for each merchant in the mandate
2. Creates standalone disclosures for each acceptable line item
3. Builds an `open_checkout` disclosure — replaces raw merchant/item objects in constraints with `{"...": "<hash>"}` SD references pointing to the standalone disclosures
4. Builds an `open_payment` disclosure — same merchant-ref replacement, plus injects a `payment.reference` constraint that cross-binds checkout ↔ payment via `checkout_disc_hash`
5. Assembles the payload with `delegate_payload` referencing the checkout and payment mandate disclosures

The result is a `kb-sd-jwt+kb` — the agent can later present only the disclosures relevant to each recipient.

**`_match_merchant_refs` / `_match_item_refs`** — private helpers that match constraint entries against the mandate's merchant/item list and return the corresponding SD hash references. Fail-closed: raise `ValueError` if a constraint references something not in the mandate.

---

## `agent.py` — Layer 3 (split credentials)

**`create_layer3_payment(mandate, agent_private_key, l2_base_jwt, payment_disclosure_b64, merchant_disclosure_b64)`**

Agent creates **L3a** for the payment network. It:
- Wraps final payment values as disclosures
- Computes `sd_hash = SHA256(L2_base_jwt + "~" + payment_disc + "~" + merchant_disc)` — this binds L3a to exactly the subset of L2 the network was shown

**`create_layer3_checkout(mandate, agent_private_key, l2_base_jwt, checkout_disclosure_b64, item_disclosure_b64)`**

Agent creates **L3b** for the merchant. Same pattern but binds to the checkout+item disclosure subset. The `transaction_id` in L3b equals `SHA256(checkout_jwt)`, which must match the `checkout_hash` in L3a — this is the cross-reference binding the two L3 credentials together.

---

## Summary flow

```
Issuer key  →  create_layer1()   →  L1 SD-JWT   (binds user pubkey)
User key    →  create_layer2_*() →  L2 SD-JWT   (binds agent pubkey, contains constraints)
Agent key   →  create_layer3_*() →  L3a + L3b   (final payment & checkout, bind to L2 subset)
```

Each layer's `sd_hash` cryptographically chains it to the layer above, making the whole delegation tamper-evident.
