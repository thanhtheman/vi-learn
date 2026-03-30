import json, base64
a = {
    "a": "something",
    "b": "something else",
    "c": {
        "key": "value"
    }
}

json_string = json.dumps(a, separators=[",",":"])
print(f"json string: {json_string} type {type(json_string)}")
byte_format = json_string.encode()
print(f"byte format: {byte_format} type {type(byte_format)}")
_base64 = base64.urlsafe_b64encode(byte_format).decode("ascii")
print(f"base 64 encoded: {_base64} type {type(_base64)}")
_base64_decode = base64.urlsafe_b64decode(_base64)
print(f"base 64 decode {_base64_decode} type {type(_base64_decode)}")
json_string_again = json.loads(_base64_decode)
print(f"python dict {json_string_again} type {type(json_string_again)}")

python_dict = json.loads(json_string)
# print(f"python dict: {python_dict} type {type(python_dict)}")