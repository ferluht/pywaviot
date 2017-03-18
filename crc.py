code = [0x5e, 0xbc, 0x61, 0xc2, 0x9d, 0x23, 0x46, 0x8c]

def __CRC8byte(data):
    crc = 0
    for i in range(8):
        if (data >> i) % 2:
            crc ^= code[i]

    return crc

def CRC8(bytes):
    crc = 0
    for byte in bytes:
        crc = __CRC8byte(ord(byte) ^ crc)

    return chr(crc)