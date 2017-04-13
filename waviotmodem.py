import serial
import time

from binascii import hexlify

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
        crc = __CRC8byte(byte ^ crc)

    return chr(crc)

class WaviotModem():

    dlmodes = {
        'NRX': 0x00,
        'CRX': 0x01,
        'DRX': 0x02,
        'TRX': 0x03
    }

    mackmodes = {
        'MACK_0': 0x00,
        'MACK_1': 0x01,
        'MACK_2': 0x02,
        'MACK_4': 0x04,
        'MACK_8': 0x08,
        'MACK_16': 0x10,
        'MACK_32': 0x20
    }

    txphymodes = {
        'UL_DBPSK_50_PROT_C': 0x14,
        'UL_DBPSK_50_PROT_D': 0x15,
        'UL_PSK_200': 0x16,
        'UL_DBPSK_400_PROT_C': 0x17,
        'UL_DBPSK_400_PROT_D': 0x18,
        'UL_PSK_500': 0x19,
        'UL_DBPSK_3200_PROT_D': 0x1A,
        'UL_PSK_5000': 0x1B,
        'UL_DBPSK_25600_PROT_D': 0x1C,
        'UL_PSK_FASTDL': 0x1D
    }

    rxphymodes = {
        'DL_PSK_200': 0x00,
        'DL_PSK_500': 0x01,
        'DL_PSK_5000': 0x02,
        'DL_PSK_FASTDL': 0x03
    }

    def __init__(self, COMname):
        self.port = serial.Serial(COMname, 115200,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE,
                    bytesize=serial.EIGHTBITS,
                    timeout=.2)

        self.port.isOpen()

    def __strtobytes__(self, str):
        if str:
            return [ord(str[i]) for i in range(0, len(str))]
        return None

    def __inttobytes__(self, n, m):
        if n:
            if n > 0x100**m:
                return None
            ret = []
            for i in range(m):
                ret.append(n%0x100)
                n /= 0x100
            return ret
        return None

    def __sendbytes__(self, command, bytes=None):
        if bytes:
            bytes = [chr(0xDD), chr(command)] + [chr(b) for b in bytes] + [CRC8(bytes), chr(0xDE)]
        else:
            bytes = [chr(0xDD), chr(command), chr(0x00), chr(0xDE)]

        # if there are system symbols replace them with escape and xor
        i = 1
        while i < len(bytes)-1:
            if bytes[i] in [chr(0xDF), chr(0xDD), chr(0xDE)]:
                t = ord(bytes[i]) ^ 0xFF
                bytes[i] = chr(0xDF)
                bytes.insert(i + 1, chr(t))
                i += 1
            i += 1

        self.port.write(chr(0xDD))
        time.sleep(0.2)
        self.port.write(bytes)
        return self.port.read(1000)

    def wakeup(self):
        self.port.write('e')
        time.sleep(0.01)
        self.__sendbytes__(0x04, [0x01,])

    def __sendstr__(self, command, data=None):
        bytes = self.__strtobytes__(data)
        return self.__sendbytes__(command, bytes)

    def get_id(self):
        data = self.__sendstr__(0x09)
        if data == '':
            return 0
        message = data[3:6]
        mcrc = data[6]
        message = [ord(c) for c in message]
        if CRC8(message) == mcrc:
            return hex(message[0]*(256**2) + message[1]*256 + message[2])
        return 0

    def TX_pending(self):
        data = self.__sendstr__(0x21)
        if data == '':
            return 0
        message = data[2]
        mcrc = data[3]
        message = [ord(c) for c in message]
        if CRC8(message) == mcrc:
            return message
        return 0

    def echo(self, data):
        echoed = self.__sendstr__(0x00, data)
        message = echoed[2:2+len(data)/2]
        mcrc = echoed[2+len(data)/2]
        if CRC8(message) == mcrc:
            return hexlify(message)
        return 0

    def transmit(self, data):
        response = self.__sendstr__(0x32, data)
        message = response[2]
        mcrc = response[3]
        message = [ord(c) for c in message]
        if CRC8(message) == mcrc:
            if message[0] == 0:
                return True
            return False
        return False

    def receive(self):
        num = self.port.inWaiting()
        mes = self.port.read(num)
        if mes.startswith(chr(0xDD)) and \
            mes.endswith(chr(0xDE)):
            if chr(0xDF) in mes:
                index = mes.index(chr(0xDF))
                mes = mes[:index] + \
                      chr(0xFF ^ ord(mes[index+1])) + \
                      mes[index+2:]
            if len(mes) > 4 and mes[1] == chr(0x10) and \
                CRC8(self.__strtobytes__(mes[2:-2])) == mes[len(mes) - 2]:
                return mes[2:-2]
        return None