import hashlib, base64, json
def _b64_url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")
disclosure_values=["rAnd0mSalt1", "email", "alice@example.com"]   
encoded = json.dumps(disclosure_values, separators=[",",":"]).encode()

# WyJyQW5kMG1TYWx0MSIsImVtYWlsIiwiYWxpY2VAZXhhbXBsZS5jb20iXQ - type <class 'str'> --> disclosure list[str]
disclosure_b64 = _b64_url_encode(encoded)
print(f"Disclosure_b64: {disclosure_b64} - type {type(disclosure_b64)}")

#b'WyJyQW5kMG1TYWx0MSIsImVtYWlsIiwiYWxpY2VAZXhhbXBsZS5jb20iXQ' - type <class 'bytes'>
disclosure_b64_ascii = disclosure_b64.encode("ascii")
print(f"Disclosure_b64_ascii: {disclosure_b64_ascii} - type {type(disclosure_b64_ascii)}")

#b'S\xd8\x06\x12\xb2\x81"\\W\x9c\x80\x86+\x9c\xb3\xe6\x19\xb4\x8f9\x92\xd93K\x94\x07 \xe7\xc7\xad\xfb['
hashed = hashlib.sha256(disclosure_b64_ascii).digest()
print(f"Hashed bytes: {hashed}")

# U9gGErKBIlxXnICGK5yz5hm0jzmS2TNLlAcg58et-1s --> _sd = [hashes]
print(f"b64 encoded hash: {_b64_url_encode(hashed)}")

names = ["chip", "thanh", "queenie"]
age = [3, 37 ,36]

for i, d in zip(names, age):
    print(f"{i} is {d} years old")