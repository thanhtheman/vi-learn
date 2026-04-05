## Explanation of `src/verifiable_intent/models/`

> This answer explains the dataclass models that define the structure of every layer and constraint type in the Verifiable Intent 3-layer SD-JWT delegation chain.

The `models/` module defines the data structures (dataclasses) for every layer and constraint type in the VI chain. Here's a breakdown by file:

---

## `issuer_credential.py` — L1 model

**`IssuerCredential`** — the root identity credential minted by the card issuer.

| Field | Purpose |
|---|---|
| `iss`, `sub`, `iat`, `exp` | Standard JWT claims |
| `vct` | Credential type URI |
| `cnf_jwk` | User's public key — binds user to credential |
| `pan_last_four`, `scheme`, `card_id` | Always-visible card info |
| `email` | The only selectively disclosable field |

`to_payload()` emits everything *except* `_sd`/disclosures — those are added by the issuance layer.

---

## `user_mandate.py` — L2 models

**`MandateMode`** — enum: `IMMEDIATE` or `AUTONOMOUS`. Controls which issuance path is taken.

**`CheckoutMandate`** — dual-mode checkout sub-credential:
- *Autonomous*: holds `cnf_jwk` (agent's public key) + `constraints` — an open mandate the agent will later fulfill
- *Immediate*: holds `checkout_jwt` + `checkout_hash` — final signed cart, no delegation
- `__post_init__` enforces mutual exclusion between the two modes

**`PaymentMandate`** — dual-mode payment sub-credential:
- *Autonomous*: `cnf_jwk` + `constraints` + `payment_instrument` + optional `risk_data`
- *Immediate*: `payee` + `currency` + `amount` + `transaction_id`
- Serializes `currency`+`amount` together as `payment_amount: {currency, amount}` in `to_dict()`

**`UserMandate`** — the top-level L2 envelope:
- Contains `nonce`, `aud` (agent URL), `sd_hash` (hash of L1), `mode`
- Holds optional `checkout_mandate` and `payment_mandate`
- In autonomous mode: also holds `merchants` and `acceptable_items` lists (each becomes a standalone selectively-disclosable disclosure)

---

## `agent_mandate.py` — L3 models

L3 is split into two credentials sent to different recipients:

**`FinalPaymentMandate`** — the actual payment instruction (L3a → network):
- `transaction_id` = SHA-256 of the checkout JWT (cross-reference to L3b)
- `payee`, `payment_amount`, `payment_instrument`

**`FinalCheckoutMandate`** — the finalized cart (L3b → merchant):
- `checkout_jwt` = merchant-signed cart JWT
- `checkout_hash` = SHA-256 of that JWT (must match `transaction_id` in L3a)

**`PaymentL3Mandate`** / **`CheckoutL3Mandate`** — envelope dataclasses that wrap the above along with JWT header claims (`nonce`, `aud`, `iat`, `sd_hash`). These are the objects passed to `create_layer3_*()` in the issuance layer.

---

## `constraints.py` — 8 constraint types

All extend `Constraint` (base class with `type` + `extra_fields` for forward-compatibility). Each sets its `type` string in `__post_init__`:

| Class | Type string | Purpose |
|---|---|---|
| `AllowedMerchantConstraint` | `mandate.checkout.allowed_merchant` | Allowlist of merchants (SD hash refs) |
| `CheckoutLineItemsConstraint` | `mandate.checkout.line_items` | Per-item allowlist with quantity |
| `AllowedPayeeConstraint` | `payment.allowed_payee` | Allowlist of payees (SD hash refs) |
| `PaymentAmountConstraint` | `payment.amount` | Per-transaction min/max in minor units |
| `ReferenceConstraint` | `payment.reference` | Cross-links payment ↔ checkout via disclosure hash |
| `PaymentBudgetConstraint` | `payment.budget` | Cumulative spend cap |
| `PaymentRecurrenceConstraint` | `payment.recurrence` | Subscription terms (merchant-initiated) |
| `AgentRecurrenceConstraint` | `payment.agent_recurrence` | Agent-managed recurring payments |

`parse_constraint(data)` is a factory function: it looks up the `type` string in `_REGISTRY`, hydrates the correct typed subclass, and routes unknown fields into `extra_fields` — making the system forward-compatible with future constraint types.

---

## `cart.py` — merchant cart structures

**`CartItem`** and **`Cart`** — simple dataclasses for constructing the merchant-signed checkout JWT payload. `Cart` holds a merchant identity + list of `CartItem`s + total. These aren't SD-JWT models themselves — they're used to build the `checkout_jwt` string that gets embedded in `FinalCheckoutMandate`.

---

## How the models relate to layers

```
IssuerCredential          →  L1 SD-JWT
UserMandate
  ├── CheckoutMandate     →  L2 checkout disclosure
  └── PaymentMandate      →  L2 payment disclosure

PaymentL3Mandate
  └── FinalPaymentMandate →  L3a payment network credential
CheckoutL3Mandate
  └── FinalCheckoutMandate→  L3b merchant credential

Cart / CartItem           →  checkout_jwt body (pre-signing)
Constraint subclasses     →  embedded in L2 mandate disclosures
```

---

## Sample `IssuerCredential` with Dummy Values

> A concrete example of constructing an `IssuerCredential` object and what its `to_payload()` output looks like — illustrating which fields are always visible vs. selectively disclosed.

```python
from verifiable_intent.models import IssuerCredential

credential = IssuerCredential(
    iss="https://www.mastercard.com",
    sub="user-123456",
    iat=1711929600,  # 2024-04-01 00:00:00 UTC
    exp=1743465600,  # 2025-04-01 00:00:00 UTC
    vct="https://credentials.mastercard.com/card",
    aud="https://wallet.example.com",
    cnf_jwk={
        "kty": "EC",
        "crv": "P-256",
        "x": "f83OJ3D2xF1Bg8vub9tLe1gHMzV76e8Tus9uPHvRVEU",
        "y": "x_FEzRu9m36HLN_tue659LNpXW6pCyStikYjKIWI5a0",
    },
    pan_last_four="4242",
    scheme="Mastercard",
    card_id="card-abc-789",
    email="alice@example.com",
)
```

And what `to_payload()` produces (the JWT body before SD processing):

```python
{
    "iss": "https://www.mastercard.com",
    "sub": "user-123456",
    "iat": 1711929600,
    "exp": 1743465600,
    "vct": "https://credentials.mastercard.com/card",
    "aud": "https://wallet.example.com",
    "cnf": {
        "jwk": {
            "kty": "EC",
            "crv": "P-256",
            "x": "f83OJ3D2xF1Bg8vub9tLe1gHMzV76e8Tus9uPHvRVEU",
            "y": "x_FEzRu9m36HLN_tue659LNpXW6pCyStikYjKIWI5a0",
        }
    },
    "pan_last_four": "4242",
    "scheme": "Mastercard",
    "card_id": "card-abc-789",
    # "email" is NOT here — it becomes a disclosure:
    # ["<salt>", "email", "alice@example.com"]  →  hashed into _sd
    "_sd": ["<sha256-hash-of-email-disclosure>"],
    "_sd_alg": "sha-256",
}
```

Key things to notice:
- `cnf.jwk` wraps the raw JWK — this is what binds Alice's device key to the credential
- `email` disappears from the payload and only its hash appears in `_sd` — the actual value travels separately as a disclosure
- Everything else (`pan_last_four`, `scheme`, etc.) is always visible to any verifier

---

## What `vct` and `aud` Mean in `IssuerCredential`

> Explains the purpose of the `vct` (Verifiable Credential Type) and `aud` (audience) fields in the L1 credential, and clarifies that "crypto" in this codebase means cryptography, not cryptocurrency.

**`vct`** stands for **Verifiable Credential Type**. It's a claim from the SD-JWT VC spec that identifies the schema/type of the credential — essentially a URI that says "this token is a Mastercard card credential, not some other kind of SD-JWT." Verifiers use it to know which fields to expect and how to validate them.

**`aud`** is the standard JWT **audience** claim — it identifies the *intended recipient* of the token. Here it's the wallet URL, meaning the L1 credential is addressed specifically to Alice's wallet. A verifier that isn't that wallet should reject it. It's marked `OPTIONAL` because not all issuance flows require audience-binding at L1 (L2 and L3 both have mandatory `aud` fields).

On the "non-crypto rail" point — this is traditional card payments (Mastercard, PAN, etc.), not blockchain. The word "crypto" in this codebase refers to *cryptography* (digital signatures, hashing, JWT), not cryptocurrency. The SD-JWT format is being applied to authorize AI agents to make card payments on a user's behalf — the underlying payment rail is entirely conventional.

---

## Deep Dive: `constraints.py`

> A detailed explanation of the 8 constraint types embedded in L2 mandates, the base `Constraint` class design, the `parse_constraint` factory function, and why `type` is set in `__post_init__` rather than at the class level.

### Overview

`constraints.py` defines the 8 constraint types that get embedded in L2 mandates (autonomous mode). Constraints are how the user limits what the agent is allowed to do.

---

### Base class: `Constraint`

```python
@dataclass
class Constraint:
    type: str = ""
    extra_fields: dict[str, Any] = field(default_factory=dict)
```

`extra_fields` is the forward-compatibility escape hatch — any unknown keys from a parsed constraint dict land here and are round-tripped back out in `to_dict()`. This means the code won't break if a future spec version adds new constraint fields.

---

### The 8 constraint types

#### Checkout constraints (go inside `CheckoutMandate`)

**`AllowedMerchantConstraint`** (`mandate.checkout.allowed_merchant`)
- `allowed_merchants`: list of SD hash refs (`{"...": "<hash>"}`)
- Limits which merchants the agent can check out with

**`CheckoutLineItemsConstraint`** (`mandate.checkout.line_items`)
- `items`: list of `{id, acceptable_items, quantity}` — each `acceptable_items` is also SD hash refs
- Restricts which SKUs/products the agent can buy and in what quantity

#### Payment constraints (go inside `PaymentMandate`)

**`AllowedPayeeConstraint`** (`payment.allowed_payee`)
- `allowed_payees`: list of SD hash refs
- Limits who can receive a payment (mirrors merchant allowlist on the payment side)

**`PaymentAmountConstraint`** (`payment.amount`)
- `currency`, `min`, `max` in integer minor units (cents)
- Per-transaction budget bounds — e.g. "never charge more than $50"

**`ReferenceConstraint`** (`payment.reference`)
- `conditional_transaction_id`: hash of the checkout disclosure
- **Auto-injected** by `create_layer2_autonomous()` — not set manually
- Cross-links the payment mandate to a specific checkout mandate, preventing the agent from paying without a matching checkout

**`PaymentBudgetConstraint`** (`payment.budget`)
- `currency`, `max` (required, must be > 0, enforced in `__post_init__`)
- Cumulative spend cap across *all* L3 transactions under this mandate pair — network-enforced

**`PaymentRecurrenceConstraint`** (`payment.recurrence`)
- `frequency`, `start_date`, optional `end_date` and `number`
- For merchant-initiated subscriptions (e.g. Netflix billing you monthly)

**`AgentRecurrenceConstraint`** (`payment.agent_recurrence`)
- `frequency`, `start_date`, `end_date` (required), optional `max_occurrences`
- For agent-initiated recurring payments (e.g. agent auto-renewing a service)

---

### `parse_constraint(data)` — the factory function

This is how constraints come back to life from raw JSON during verification:

1. Looks up `data["type"]` in `_REGISTRY`
2. If unknown type → returns a plain `Constraint` with `extra_fields` (no data loss)
3. If known → inspects the dataclass fields, routes known keys to `kwargs` and unknown keys to `extra_fields`, then instantiates the right subclass

The key line:
```python
known_fields = {f.name for f in cls.__dataclass_fields__.values()} - {"type", "extra_fields"}
```
This introspects the dataclass at runtime to know which fields belong to the subclass, so no manual field listing is needed.

---

### Why `type` is set in `__post_init__` not in the class body

Each subclass does `self.type = "payment.amount"` in `__post_init__` rather than as a class-level default. This is because `@dataclass` inheritance means the base `type: str = ""` field is inherited — overriding it at the class level would require repeating the field declaration. `__post_init__` is simpler and guarantees the type string is always correct regardless of how the object was constructed.
