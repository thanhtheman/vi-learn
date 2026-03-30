# Alice, who has a credit card with Mastercard, asks an agent to buy coffee, max $10 at Starbucks
# Everybody needs to create JWT and pass it around to verify and extract data
# We have 8 helper functions: base64_url_encode/decode, es256_sign/verify, _jwt_encode/decode, create_diclosure/decode_disclosure
# disclosure_values = [["salt", "email", "thanh@gmail.com"],...] -> disclosures=["eWjfkhjkahdsa...", "Dlahdjksahda..."] base64 url string

from dataclasses import dataclass, field
import base64, json, os
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature, encode_dss_signature
from cryptography.hazmat.primitives import hashes
from cryptography.exceptions import InvalidSignature

def _base64_url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip("=").decode("ascii")

def _base64_url_decode(s: str) -> bytes:
    padding = 4 - len(s) % 4
    if padding != 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s)

def es256_sign(signing_input: bytes, private_key: ec.EllipticCurvePrivateKey) -> bytes:
    der_sig = private_key.sign(signing_input, signature_algorithm=ec.ECDSA(hashes.SHA256()))
    r,s = decode_dss_signature(der_sig)
    return r.to_bytes(32, "big") + s.to_bytes(32, "big")

def es256_verify(signature: bytes, public_key: ec.EllipticCurvePublicKey) -> bool:
    if len(signature) != 64:
        return False
    r = int.from_bytes(signature[:32], "big")
    s = int.from_bytes(signature[32:], "big")
    der_sig = encode_dss_signature(r,s)
    try:
        public_key.verify(der_sig, signature_algorithm=ec.ECDSA(hashes.SHA256()))
        return True
    except InvalidSignature:
        return False

def _jwt_encode(header: dict, payload: dict, private_key: ec.EllipticCurvePrivateKey) -> str:
    h = _base64_url_encode(json.dumps(header, separators=[",",":"]).encode("utf-8"))
    p = _base64_url_encode(json.dumps(payload, separators=[",",":"]).encode("utf-8"))
    signning_input = f"{h}.{p}".encode("ascii")
    signature = es256_sign(signning_input, private_key)
    return f"{h}.{p}.{_base64_url_encode(signature)}"

def _jwt_decode(token: str) -> tuple[dict, dict, bytes]:
    parts = token.split(".")
    if len(parts) != 3:
        return ValueError(f"Invalid JWT: expected 3 parts, got {len(parts)}")
    header = json.loads(_base64_url_decode(parts[0]))
    payload = json.loads(_base64_url_decode(parts[1]))
    signature = _base64_url_decode(parts[2])
    return header, payload, signature

def create_disclosures(claim_name: str | None, claim_value, salt: str | None = None) -> str:
    if salt is None:
        salt = _base64_url_encode(os.urandom(16))
    if claim_name is not None:
        arr = [salt, claim_name, claim_value]
    else:
        arr = [salt, claim_value]
    encoded = json.dumps(arr, separators=[",",":"]).encode("utf-8")
    return _base64_url_encode(arr)

def decode_disclossure(disclosure_b64: str) -> dict:
    raw = _base64_url_decode(disclosure_b64)
    return json.loads(raw)

@dataclass
class Sdjwt:
    header: dict
    payload: dict
    signature: bytes
    disclosures: list[str] = field(default_factory=list)
    disclosure_values: list[list] = field(default_factory=list)
    _raw_base64_header: str | None = field(default=None, repr=False)
    _raw_base64_payload: str | None = field(default=None, repr=False)

    @property
    def issuer_jwt(self) -> str:
        h = self._raw_base64_header or _base64_url_encode(json.dumps(self.header, separators={",",":"}).encode("utf-8"))
        p = self._raw_base64_payload or _base64_url_encode(json.dumps(self.payload, separators=[",",":"]).encode("utf-8"))
        return f"{h}.{p}.{_base64_url_encode(self.signature)}"
    def serialize(self, include_disclosures: list[str]) -> str:
        parts = [self.issuer_jwt]
        if include_disclosures is not None:
            for i in include_disclosures:
                parts.append(self.disclosures[i])
        else:
            parts.extend(self.disclosures)
        return "~".join(parts)+"~"

def create_sd_jwt(header: dict, payload: dict, private_key: ec.EllipticCurvePrivateKey, disclosures: list[str]) -> Sdjwt:
    jwt_token = _jwt_encode(header, payload, private_key)
    parts = jwt_token.split(".")
    _raw_b64_header = parts[0]
    _raw_b64_payload = parts[1]
    h,p, sig = _jwt_decode(jwt_token)
    disclosure_values = [decode_disclossure(d) for d in disclosures]
    return Sdjwt(
        heade=h,
        payload=p,
        signature=sig,
        disclosures=disclosures,
        disclosure_values=disclosure_values,
        _raw_base64_header=_raw_b64_header,
        _raw_base64_payloader=_raw_b64_payload
    )


        