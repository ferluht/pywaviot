import serial
import time
import threading

from binascii import hexlify, unhexlify

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

    received_messages = []
    downlink_messages = []

    def __init__(self, COMname=None):

        if not COMname:
            return

        self.port = serial.Serial(COMname, 115200,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE,
                    bytesize=serial.EIGHTBITS,
                    timeout=.2)

        self.port.isOpen()

        self.mode = None
        self.handshake = None
        self.maxlen = None
        self.txfreq = None
        self.rxfreq = None
        self.ant = None
        self.dl_id = None
        self.heartbeat = None
        self.version = None
        self.flags = None

        self.th = threading.Thread(target=self.receiver)
        self.th.start()

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

    def __sendbytes__(self, command, bytes=None, receive=True):
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
        time.sleep(0.01)
        self.port.write(bytes)
        if receive:
            time.sleep(0.2)
        return self.receive()

    def wakeup(self):
        self.port.write('e')
        time.sleep(0.01)
        self.__sendbytes__(0x04, [0x01,])

    def __sendstr__(self, command, data=None, receive=True):
        bytes = self.__strtobytes__(data)
        return self.__sendbytes__(command, bytes, receive)

    def get_id(self):
        data = self.__sendstr__(0x09)
        if not data or data == '':
            return 0
        return hexlify(data)

    def transmit_buffer_size(self):
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
        return self.__sendstr__(0x32, data, receive=False)

    def set_mode(self, receive_mode, mack_mode,
                    tx_phy_channel, rx_phy_channel,
                    tx_pwr, num_of_retries):

        return self.__sendbytes__(0x40, [0x80, receive_mode, mack_mode, tx_phy_channel,
                                        rx_phy_channel, tx_pwr, num_of_retries])

    def nearlink_enable(self):

        return self.__sendbytes__(0x40, [0x40, 0x02, 0x01, 0x1D, 0x03, 0x1A, 0x05])

    def read_mode(self, rw, receive_mode, mack_mode,
                    tx_phy_channel, rx_phy_channel,
                    tx_pwr, num_of_retries):

        return self.__sendbytes__(0x40, [0x00, receive_mode, mack_mode, tx_phy_channel,
                                        rx_phy_channel, tx_pwr, num_of_retries])

    def set_handshake(self, handshake_mode, mack_mode):
        return self.__sendbytes__(0x40, [0x41, handshake_mode, mack_mode])

    def set_maxlen(self, maxlen):
        return self.__sendbytes__(0x40, [0x82, maxlen])

    def set_txfreq(self, txfreq):
        bytes = []#self.__inttobytes__(txfreq, 4)
        bytes.append((txfreq >> 24) & 0xFF)
        bytes.append((txfreq >> 16) & 0xFF)
        bytes.append((txfreq >> 8) & 0xFF)
        bytes.append(txfreq & 0xFF)
        return self.__sendbytes__(0x40, [0x43,] + bytes)

    def set_rxfreq(self, rxfreq):
        bytes = []  # self.__inttobytes__(txfreq, 4)
        bytes.append((rxfreq >> 24) & 0xFF)
        bytes.append((rxfreq >> 16) & 0xFF)
        bytes.append((rxfreq >> 8) & 0xFF)
        bytes.append(rxfreq & 0xFF)
        return self.__sendbytes__(0x40, [0x44,] + bytes)

    def set_ant(self, txpwr, txant, rxant):
        return self.__sendbytes__(0x40, [0x45, txpwr, txant, rxant])

    def set_dl(self, dlID):
        bytes = self.__inttobytes__(dlID, 3)
        return self.__sendbytes__(0x40, [0x46,] + bytes)

    def transmit_fastDL(self, data):
        return self.__sendstr__(0x43, data)

    def enable_fastDL(self):
        return self.__sendstr__(0x43)

    def config_maxlen(self, rw, handshake_mode, mack_mode):

        return self.__sendbytes__(0x40, [rw, handshake_mode, mack_mode])

    def read_all_settings(self):
        self.mode = self.__strtobytes__(self.__sendbytes__(0x40, [0x00, ])[1:])
        self.handshake = self.__strtobytes__(self.__sendbytes__(0x40, [0x01, ])[1:])
        self.maxlen = self.__strtobytes__(self.__sendbytes__(0x40, [0x02, ])[1:])
        self.txfreq = self.__strtobytes__(self.__sendbytes__(0x40, [0x03, ])[1:])
        self.rxfreq = self.__strtobytes__(self.__sendbytes__(0x40, [0x04, ])[1:])
        self.ant = self.__strtobytes__(self.__sendbytes__(0x40, [0x05, ])[1:])
        self.dl_id = self.__strtobytes__(self.__sendbytes__(0x40, [0x06, ])[1:])
        self.heartbeat = self.__strtobytes__(self.__sendbytes__(0x40, [0x07, ])[1:])
        self.version = self.__strtobytes__(self.__sendbytes__(0x40, [0x0A, ])[1:])
        self.flags = self.__strtobytes__(self.__sendbytes__(0x40, [0x0B, ])[1:])

    def write_all_settings(self):
        self.mode = self.__strtobytes__(self.__sendbytes__(0x40, [0x80, ] + self.mode)[1:])
        self.handshake = self.__strtobytes__(self.__sendbytes__(0x40, [0x81, ] + self.handshake)[1:])
        self.maxlen = self.__strtobytes__(self.__sendbytes__(0x40, [0x82, ] + self.maxlen)[1:])
        self.txfreq = self.__strtobytes__(self.__sendbytes__(0x40, [0x83, ] + self.txfreq)[1:])
        self.rxfreq = self.__strtobytes__(self.__sendbytes__(0x40, [0x84, ] + self.rxfreq)[1:])
        self.ant = self.__strtobytes__(self.__sendbytes__(0x40, [0x85, ] + self.ant)[1:])
        self.dl_id = self.__strtobytes__(self.__sendbytes__(0x40, [0x86, ] + self.dl_id)[1:])
        self.heartbeat = self.__strtobytes__(self.__sendbytes__(0x40, [0x87, ] + self.heartbeat)[1:])
        # self.version = self.__strtobytes__(self.__sendbytes__(0x40, [0x8A, ] + self.version)[1:])
        self.flags = self.__strtobytes__(self.__sendbytes__(0x40, [0x8B, ] + self.flags)[1:])

    def set_fastDL(self):
        self.read_all_settings()

        self.maxlen[0] = 0x80
        self.mode[0] = 0x03
        self.mode[2] = 0x1D
        self.mode[3] = 0x03
        self.handshake[0] = 0x00
        self.txfreq = [0x1A, 0xA4, 0xAD, 0xC0]
        self.rxfreq = [0x1A, 0xA4, 0xAD, 0xC0]
        self.dl_id = [0xFF, 0x00, 0x00, 0x00]
        # self.dl_id = [0x00, 0x6F, 0xB2, 0x6F]
        self.write_all_settings()

    def receive(self):
        if self.received_messages:
            return self.received_messages.pop()

    def receive_downlink(self):
        if self.downlink_messages:
            return self.downlink_messages.pop()

    def receiver(self):
        while 1:
            time.sleep(0.05)
            num = self.port.inWaiting()
            mes = self.port.read(num)
            if mes.startswith(chr(0xDD)) and \
                mes.endswith(chr(0xDE)):
                if chr(0xDF) in mes:
                    index = mes.index(chr(0xDF))
                    mes = mes[:index] + \
                          chr(0xFF ^ ord(mes[index+1])) + \
                          mes[index+2:]
                if len(mes) > 4 and \
                    CRC8(self.__strtobytes__(mes[2:-2])) == mes[len(mes) - 2]:
                    if ord(mes[1]) == 0x10:
                        self.downlink_messages.append(mes[2:-2])
                    self.received_messages.append(mes[2:-2])