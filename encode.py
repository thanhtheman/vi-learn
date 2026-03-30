import os, base64, json, hashlib

# Salt: b'\xc64\xcd2\xdb\x1c\xf7\x02\xee\xc3\x11\x11p\xa38\x83'
salt = os.urandom(16)
print(f"Salt: {salt}")

# Encoded Salt: b'wN4s9n2X8u5v1j3z5m7Qw=='
encoded_salt = base64.urlsafe_b64encode(salt)
print(f"Encoded Salt: {encoded_salt}")

#'==' doesn't work well with URL encoding, so we can remove it for better compatibility
#Encoded Salt without padding: b'5o7DEPdUWmKz04_X_rNmog'
encoded_salt = encoded_salt.rstrip(b'=')
print(f"Encoded Salt without padding: {encoded_salt}")

# we need to convert this into a string for JWT usage
#Salt: b'\x92J\xbcj\xc6\x04\x98\xc3}\x1dh\xa9\x08\xb5N5'
#Encoded Salt: b'kkq8asYEmMN9HWipCLVONQ=='
#Encoded Salt without padding: b'kkq8asYEmMN9HWipCLVONQ'
#Salt as string: kkq8asYEmMN9HWipCLVONQ
salt_str = encoded_salt.decode('ascii')
print(f"Salt as string: {salt_str}")



def _base64_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")

def _base64_decode(s: str) -> bytes:
    padding = 4 - len(s) % 4
    if padding != 0:
        s += "=" * padding
    return base64.urlsafe_b64decode(s)

def _generate_salt ():
    return _base64_encode(os.urandom(16))

# WyJUaGFuaCIsInRoYW5oQGdtYWlsLmNvbSIsIk9SYW9QSGFSOGN2Ty02QllGSnlxR3ciXQ
def create_disclosure(claim_name: str | None, claim_value, salt: str | None = None ):
    if salt == None:
        salt = _generate_salt()
    if claim_name is not None:
        arr = [claim_name, claim_value, salt]
    encoded = json.dumps(arr, separators=[",",":"]).encode("utf-8")
    print(f"Encoded json dumps: {encoded}")
    return _base64_encode(encoded)
result= create_disclosure("email", "thanh@gmail.com")
print(result) 
# print(_base64_decode(result))

def decode_disclosure(disclosure_b64: str):
    raw = _base64_decode(disclosure_b64)
    return json.loads(raw)
print(f"decoded disclosure: {decode_disclosure(result)}")

def hash_disclosure(disclosure_b64: str) -> str:
    print(f"dislosure_b64 ascii encode: {disclosure_b64.encode("ascii")}")
    digest = hashlib.sha256(disclosure_b64.encode("ascii")).digest()
    print(f"hash: {digest}")
    return _base64_encode(digest)

print(f"base64 encoded hashed: {hash_disclosure(result)}")

