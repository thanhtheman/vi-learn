from __future__ import annotations
from dataclasses import dataclass, field
# L1 - Mastercard
@dataclass
class IssuerCredentials:
    iss: str
    sub: str
    iat: int
    exp: int
    vct: str = "https://credentials.mastercard.com/card"
    aud: str | None = None
    cnf_jwk: dict = field(default_factory=dict)

    pan_last_four: str = ""
    scheme: str = ""
    card_id: str | None = None

    #selective disclosure
    email: str | None = None

    def to_payload(self) -> dict:
        d = {
            "iss": self.iss,
            "sub": self.sub,
            "iat": self.iat,
            "exp": self.exp,
            "vct": self.vct,
            "cnf": {
                "jwk": self.cnf_jwk
            }
        }
        if self.aud:
            d["aud"] = self.aud
        d["pan_last_four"] = self.pan_last_four
        d["scheme"] = self.scheme
        if self.card_id is not None:
            d["card_id"] = self.card_id
        return d


# L2 - Alice
from enum import Enum
from typing import Any

# Constraints

@dataclass
class Constraint:
    type: str = ""
    extra_fields: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = {"type": self.type}
        d.update(self.extra_fields)
        return d

@dataclass
class AllowedMerchantConstraint(Constraint):
    allowed_merchants: list[dict] = field(default_factory=list)
    
    def __post_init__(self):
        self.type = "mandate.checkout.allowed_merchant"
    
    def to_dict(self):
        d = {
            "type": self.type,
            "allowed_merchants": self.allowed_merchants
        }
        d.update(self.extra_fields)
        return d

@dataclass
class CheckoutLineItemsConstraint(Constraint):
    items: list[dict] = field(default_factory=list)
    def __post_init__(self):
        self.type = "mandate.checkout.line_items"
    
    def to_dict(self):
        d: dict[str, Any] = {
            "type": self.type,
            "line_items": self.items,
        }
        d.update(self.extra_fields)
        return d

@dataclass
class AllowedPayeeConstraint(Constraint):
    allowed_payee: list[dict] = field(default_factory=list)
    def __post_init__(self):
        self.type = "payment.allowed_payee"
    
    def to_dict(self):
        d = {
            "type": self.type,
            "allowed_payee": self.allowed_payee
        }
        d.update(self.extra_fields)
        return d

@dataclass
class PaymentAmountConstraint(Constraint):
    currency: str = "USD"
    min: int | None = None
    max: int | None = None

    def __post_init__(self):
        self.type = "payment.amount"

    def to_dict(self):
        d = dict[str, Any] = {
            "currency": self.currency,
        }
        if self.min is not None:
            d["min"] = self.min
        if self.max is not None:
            d["max"] = self.max
        d.update(self.extra_fields)
        return d

@dataclass
class ReferenceConstraint(Constraint):
    conditional_transaction_id: str =""
    def __post_init__(self):
        self.type = "payment.reference"
    def to_dict(self):
        d = {
            "type": self.type,
            "conditional_transaction_id": self.conditional_transaction_id
        }
        d.update(self.extra_fields)
        return d
    
@dataclass
class PaymentBudgetConstraint(Constraint):
    currency: str = "USD"
    max: int = 0

    def __post_init__(self):
        self.type = "payment.budget"
        if self.max <= 0:
            raise ValueError("PaymentBudgetConstraint.mx must be a positive integer")
    
    def to_dict(self):
        d: dict[str, Any] = {
            "type": self.type,
            "currency": self.currency,
            "max": self.max
        }
        d.update(self.extra_fields)
        return d

@dataclass
class PaymentRecurrenceConstraint(Constraint):
    """Subscription setup terms for merchant-initiated recurring. Network-enforced."""

    frequency: str = ""  # e.g. "MONTHLY", "ANNUALLY"
    start_date: str = ""  # ISO 8601
    end_date: str | None = None  # ISO 8601, optional
    number: int | None = None  # Max occurrences, optional

    def __post_init__(self):
        self.type = "payment.recurrence"

    def to_dict(self) -> dict:
        d: dict[str, Any] = {
            "type": self.type,
            "frequency": self.frequency,
            "start_date": self.start_date,
        }
        if self.end_date is not None:
            d["end_date"] = self.end_date
        if self.number is not None:
            d["number"] = self.number
        d.update(self.extra_fields)
        return d


@dataclass
class AgentRecurrenceConstraint(Constraint):
    """Agent-managed recurring transaction terms. Network-enforced."""

    frequency: str = ""  # e.g. "WEEKLY", "MONTHLY"
    start_date: str = ""  # ISO 8601
    end_date: str = ""  # ISO 8601, required
    max_occurrences: int | None = None  # Optional cap

    def __post_init__(self):
        self.type = "payment.agent_recurrence"

    def to_dict(self) -> dict:
        d: dict[str, Any] = {
            "type": self.type,
            "frequency": self.frequency,
            "start_date": self.start_date,
            "end_date": self.end_date,
        }
        if self.max_occurrences is not None:
            d["max_occurrences"] = self.max_occurrences
        d.update(self.extra_fields)
        return d


_REGISTRY: dict[str, type[Constraint]] = {
    "mandate.checkout.allowed_merchant": AllowedMerchantConstraint,
    "mandate.checkout.line_items": CheckoutLineItemsConstraint,
    "mandate.allowed_payee": AllowedPayeeConstraint,
    "payment.amount": PaymentAmountConstraint,
    "payment.reference": ReferenceConstraint,
    "payment.budget": PaymentBudgetConstraint,
    "payment.recurrence": PaymentRecurrenceConstraint,
    "payment.agent_recurrence": AgentRecurrenceConstraint
} 


def parse_constraint(data: dict) -> Constraint:
    if isinstance(data, Constraint):
        return Constraint(type="unknown")
    ctype = data.get("type", "")
    cls = _REGISTRY.get(ctype)
    if cls is None:
        return Constraint(type=ctype, extra_fields={k: v for k,v in data.items() if k != "type"})
    known_fields = {f.name for f in cls.__dataclass_fields__.values()} - {"type", "extra_fields"}
    kwargs = {}
    extra = {}
    for k, v in data.items():
        if k != "type":
            continue
        if k in known_fields:
            kwargs[k] = v
        else:
            extra[k] = v
    obj = cls(type=ctype, **kwargs)
    obj.extra_fields = extra
    return obj


class MandateMode(str, Enum):
    IMMEDIATE = "IMMEDIATE"
    AUTONOMOUS = "AUTONOMOUS"

@dataclass
class CheckoutMandate:
    vct: str = "mandate.checkout.open"
    cnf_jwk: dict | None = None
    cnf_kid: str | None = None
    constraints: list[Constraint] = field(default_factory=list)
    checkout_jwt: str | None = None
    checkout_hash: str | None = None

    def __post_init__(self):
        if self.cnf_jwk and self.checkout_jwt is not None:
            raise ValueError("CheckoutMandate cannot have both cnf_jwk(autonomous) and checkout_jwt(immediate)")
    def to_dict(self) -> dict:
        d: dict[str, Any] = {
            "vct": self.vct
        }
        if self.cnf_jwk:
            cnf: dict[str, Any] = {"jwt": self.cnf_jwk}
            if self.cnf_kid:
                cnf["kid"] = self.cnf_kid
            d["cnf"] = cnf
        d["constraints"] = {c.to_dict() for c in self.constraints}
        if self.checkout_jwt is not None:
            d["checkout_jwt"] = self.checkout_jwt
        if self.checkout_hash is not None:
            d["checkout_hash"] = self.checkout_hash
        return d
    
@dataclass
class PaymentMandate:
    vct: str = "mandate.payment.open"
    cnf_jwt: dict[str, Any] | None = None
    cnf_kid: str | None = None
    constraints: list[Constraint] = field(default_factory=list)
    payment_instruments: dict | None = None
    risk_data: dict | None = None
    payee: dict | None = None
    currency: str | None = None
    amount: int | None = None
    transaction_id: str | None = None

    def __post_init__(self):
        has_immediate = self.amount is not None
        has_autonomous = self.cnf_jwt is not None
        if has_autonomous and has_immediate:
            raise ValueError("PaymentMandate cannot have both cnf_jwt(autonomous) and amount (immediate)")
    
    def to_dict(self) -> dict:
        d: dict[str, Any] = {"vct": self.vct}
        if self.cnf_jwt is not None:
            cnf: dict[str, Any] = {"jwt": self.cnf_jwt}
            if self.cnf_kid is not None:
                cnf["kid"] = self.cnf_kid
            d["cnf"] = cnf
        if self.payment_instruments is not None:
            d["payment_instruments"] = self.payment_instruments
        if self.risk_data is not None:
            d["risk_data"] = self.risk_data
        if self.currency is not None and self.amount is not None:
            d["payment_amount"] = {"currency": self.currency, "amount": self.amount}
        if self.transaction_id is not None:
            d["transaction_id"] = self.transaction_id
        return d
    
@dataclass
class UserMandate:
    nonce: str
    aud: str
    iat: int
    mode: MandateMode
    iss: str | None = None
    exp: int | None = None
    sd_hash: str = ""
    prompt_summary: str | None = None
    checkout_mandage: CheckoutMandate | None = None
    payment_mandate: PaymentMandate | None = None
    merchants: list[dict] = field(default_factory=list)
    acceptable_items: list[dict] = field(default_factory=list)

