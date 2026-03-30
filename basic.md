base64 = 64 characters (A-Z, a-z, +, /)
To represent each character, we need to know how many bits it takes?
Each bit is either 1 or 0.
So we need 2^6 = 64
--> each character is 6-bit

However, each byte is 8-bit, that's how the computer is saved and process data. So how can we "bridge" them?
The common denominator for both 6 and 8 is 24. It has to be 24 slots so that base64 can allocate the characters according to its setup 6-bit, but at the same time, the computer camn group them into 8-bit slots as well to process.
The conversion rate is: 4 characters (base 64 = 6x4) = 3 bytes (8x3)
This ratio must be maintained. Any leftover "fake" bits must be rounded up to satisfy this conversion rate

Why a random 16-bytes object? --> because it is recommended for cryptographic strength. It has nothing to do with 64 or 4
```b'\x92 J \xbc j \xc6 \x04 \x98 \xc3 } \x1d h \xa9 \x08 \xb5 N 5'`` --> \xx is 1 byte, if it is a letter J or j, that counts as 1 byte too, not all bytes are ascii-printable. So we always end up with 16 blocks.
16 bytes = 16 x 8 bit = 128 bits.
But, base64 only has 6-bit slot
so to contain 128 bit , we need 128:6 = 21.33 slots
The last correct ratio is only 20 chars 6 x 20 = 120 bits, the next satisfied point is 24 chars, which is 6 x 24 = 144 bits. Yes, we need to add 4-character block each time, we can't add 2 or 3 characters as it will violate the conversion ratio.
So we need 21 6-bit slots, that will hold 6 x 21 = 126 bits, we will need 2 bits more. We add a new 6-bit slot, which will leave us with 4 bits (0000). In the 22nd slot/character, we only have 2 real bits and 4 "fake" bits of '0
When the decoder, "we need to have a multiple of 3 bytes (24 bits), to be in sync with the base64 6-bit setup", in  sees XXXX at the end, it either 8-bit (1 byte), 16-bit (2 bytes) man, it can't be just 4-bit. Adding another 6-bit (base64 setup) will make it 10-bit, well, still not 8-bit or 16 bit, so we need to add one more 6-bit, now it is 16-bit, perfectly matches multiple of 3 bytes" --> so we need 24 characters then. The last 2 just "="
That's why we always add "==" as padding to fill up the lot.  
