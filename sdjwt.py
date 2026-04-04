# creating SD-JWT first
# resolve disclosure: turning _sd -> set, hash disc_str to compare with set, if len(disc_val) = 3, adding name-value as key-value pair into result.
# if len(disc_val) is 2 -> array element: hash disc_str and pair them with disc_val in an array call hash-value-pair (dict)
# loop through delegate_payload arrays: item, taking out the hash (item["..."]) as ref-hash, check if ref_hash is in the hash-value-pair dictionary, if yes. Adding the value ([salt, value]) into the resolve_delegate, if they are not on the list, then just add the whole item --> which still has the placeholder

from dataclasses import dataclass, field
import base64, json, os, hashlib
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature, encode_dss_signature
from cryptography.exceptions import InvalidSignature

def _b64_url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")

def _b64_url_decode(s: str) -> bytes:
    padding = 4 - len(s)%4
    if padding != 4:
        s += "="*padding
    return base64.urlsafe_b64decode(s)

def es256_sign(input: bytes, private_key: ec.EllipticCurvePrivateKey) -> bytes:
    der_sig = private_key.sign(input, ec.ECDSA(hashes.SHA256()))
    r, s = decode_dss_signature(der_sig)
    return r.to_bytes(32, "big")+s.to_bytes(32, "big")

def es256_verify(input: bytes, signature: bytes, public_key: ec.EllipticCurvePublicKey) -> bool:
    if len(signature) != 64:
        return False
    r = int.from_bytes(signature[:32], "big")
    s = int.from_bytes(signature[32:], "big")
    der_sig = encode_dss_signature(r,s)
    try:
        public_key.verify(der_sig, input, ec.ECDSA(hashes.SHA256()))
        return True
    except InvalidSignature:
        return False

def _jwt_encode(header: dict, payload: dict, private_key: ec.EllipticCurvePrivateKey) -> str:
    h = _b64_url_encode(json.dumps(header, separators=[",",":"]).encode("utf-8"))
    p = _b64_url_encode(json.dumps(payload, separators=[",",":"]).encode("utf-8"))
    singning_input = f"{h}.{p}".encode("ascii")
    signature = es256_sign(singning_input, private_key)
    return f"{h}.{p}.{_b64_url_encode(signature)}"

def _jwt_decode(jwt: str) -> tuple [dict, dict, bytes]:
    parts = jwt.split(".")
    if len(parts) != 3:
        raise ValueError(f"Invalid JWT: expected 3, got {len(parts)}")
    header = json.loads(_b64_url_decode(parts[0]))
    payload = json.loads(_b64_url_decode(parts[1]))
    signature = _b64_url_decode(parts[2])
    return header, payload, signature

def create_disclosures(claim_name: str | None, claim_value, salt: str | None = None) -> str:
    if salt is None:
        salt = _b64_url_encode(os.urandom(16))
    if claim_name is not None:
        arr = [salt, claim_name, claim_value]
    else:
        arr = [salt, claim_value]
    encoded = json.dumps(arr, separators=[",",":"]).encode("utf-8")
    return _b64_url_encode(encoded)

def decode_disclosure(disclosure_b64: str) -> list:
    raw = _b64_url_decode(disclosure_b64)
    return json.loads(raw)

def hash_disclosure(disclosure_b64: str) -> str:
    digest = hashlib.sha256(disclosure_b64.encode("ascii")).digest()
    return _b64_url_encode(digest)
 
def hash_bytes(data: bytes) -> str:
    digest = hashlib.sha256(data).digest()
    return _b64_url_encode(digest)

@dataclass
class Sdjwt:
    header: dict
    payload: dict
    signature: bytes
    disclosures: list[str] = field(default_factory=list)
    disclosure_values: list[list] = field(default_factory=list)
    _raw_header_base64: str | None = field(default=None, repr=False)
    _raw_payload_base64: str | None = field(default=None, repr=False)

    @property
    def issuer_jwt(self) -> str:
        h = self._raw_header_base64 or _b64_url_encode(json.dumps(self.header, separators=[",",":"]).encode("utf-8"))
        p = self._raw_payload_base64 or _b64_url_encode(json.dumps(self.payload, separators=[",",":"]).encode("utf-8"))
        return f"{h}.{p}.{_b64_url_encode(self.signature)}"
    
    def serialize(self, include_disclosure: list[int]) -> str:
        parts = [self.issuer_jwt]
        if include_disclosure is not None:
            for i in include_disclosure:
                parts.append(self.disclosures[i])
        else:
            parts.extend(self.disclosures)
        return "~".join(parts)+"~"

def create_sd_jwt(header: dict, payload: dict, disclosures: list[str], private_key: ec.EllipticCurvePrivateKey):
    jwt = _jwt_encode(header, payload, private_key)
    parts = jwt.split(".")
    _raw_h_b64, _raw_p_b64 = parts[0], parts[1]
    h, p, sig = _jwt_decode(jwt)
    disclosure_values = [decode_disclosure(d) for d in disclosures]
    return Sdjwt(
        header=h,
        payload=p,
        signature=sig,
        disclosures=disclosures,
        disclosure_values=disclosure_values,
        _raw_header_base64 = _raw_h_b64,
        _raw_payload_base64=_raw_p_b64
    )

def decode_serialized_sd_jwt(serialized: str) -> Sdjwt:
    parts = serialized.split("~")
    jwt = parts[0]
    jwt_parts = jwt.split(".")
    _raw_h, _raw_p = jwt_parts[0], jwt_parts[1]
    h, p, sig = _jwt_decode(jwt)
    disclosures = [h for h in parts[1:] if h]
    disclosure_values =[decode_disclosure(d) for d in disclosures]
    return Sdjwt (
        header=h,
        payload=p,
        signature=sig,
        disclosures=disclosures,
        disclosure_values=disclosure_values,
        _raw_header_base64 = _raw_h,
        _raw_payload_base64=_raw_p
    )

def verify_sd_jwt_signature(sd_jwt: Sdjwt, public_key: ec.EllipticCurvePublicKey) -> bool:
    try:
        h = _b64_url_encode(json.dumps(sd_jwt.header, separators=[",",":"]).encode("utf-8"))
        p = _b64_url_encode(json.dumps(sd_jwt.payload, separators={",",":"}).encode("utf-8"))
    except (ValueError, TypeError):
        return False
    signing_input = f"{h}.{p}".encode("ascii")
    return es256_verify(signing_input, sd_jwt.signature, public_key)

def resolve_disclosures(sd_jwt: Sdjwt) -> dict:
    result = dict(sd_jwt.payload)
    _sd_raw = result.get("_sd", [])
    if isinstance(_sd_raw, list):
        sd_hashes = {h for h in _sd_raw if isinstance(h, str)}
    else:
        sd_hashes = set()

    for disc_str, disc_val in zip (sd_jwt.disclosures, sd_jwt.disclosure_values):
        disc_hash = hash_disclosure(disc_str)
        if disc_hash in sd_hashes:
            if len(disc_val) == 3:
                result[disc_val[1]] = disc_val[2]
            elif len(disc_val) == 2:
                pass
    delegate_payload = result.get("delegate_payload", [])
    if delegate_payload and isinstance(delegate_payload, list):
        resolved_delegate = []
        hash_value_pair = {}
        for disc_str, disc_val in zip( sd_jwt.disclosures, sd_jwt.disclosure_values):
            hash_value_pair[hash_disclosure(disc_str)] = disc_val
        for item in delegate_payload:
            if isinstance(item, dict) and "..." in item:
                ref_hash = item["..."]
                if ref_hash in hash_value_pair:
                    dv = hash_value_pair[ref_hash]
                    resolved_delegate.append(dv[-1])
                else:
                    resolved_delegate.append(item)
            else:
                resolved_delegate.append(item)
        result["delegate_payload"] = resolved_delegate
    return result

@dataclass
class KbSdJwt():
    holder_header: str
    holder_payload: str
    signature: bytes

    @property
    def jwt(self) -> str:
        h = _b64_url_encode(json.dumps(self.holder_header, separators=[",",":"]).encode())
        p = _b64_url_encode(json.dumps(self.holder_payload, separators=[",",":"]).encode())
        return f"{h}.{p}.{_b64_url_encode(self.signature)}"

@dataclass
class SdKbWithJwt():
    sd_jwt: Sdjwt
    kb_jwt: KbSdJwt
    disclosed_indices: list[int] | None = None

    @property
    def sd_kb_jwt(self) -> str:
        serialized = self.sd_jwt.serialize(include_disclosure=self.disclosed_indices)
        return serialized + self.kb_jwt.jwt

def create_kb_sd_jwt(
        sd_jwt: Sdjwt,
        holder_header: str,
        holder_payload: str,
        private_key: ec.EllipticCurvePrivateKey,
        disclosed_indices: list[int] | None = None
) -> SdKbWithJwt:
    if "sd_hash" not in holder_payload:
        serialized = sd_jwt.serialize(include_disclosure=disclosed_indices)
        holder_payload["sd_hash"] = hash_bytes(serialized.encode("ascii"))
    
    jwt = _jwt_encode(holder_header, holder_payload, private_key)
    h, p, signature = _jwt_decode(jwt)
    kb_jwt = KbSdJwt(h, p, signature)
    return SdKbWithJwt(sd_jwt, kb_jwt, disclosed_indices)

def verify_kb_jwt(kb_jwt: KbSdJwt, public_key: ec.EllipticCurvePublicKey) -> bool:
    h = _b64_url_encode(json.dumps(kb_jwt.holder_header, separators=[",",":"]).encode())
    p = _b64_url_encode(json.dumps(kb_jwt.holder_payload, separators=[",",":"]).encode())
    signing_input = f"{h}.{p}".encode("ascii")
    return es256_verify(signing_input, kb_jwt.signature, public_key)