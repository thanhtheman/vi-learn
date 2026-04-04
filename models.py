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