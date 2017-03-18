import serial
import time
import crc

from binascii import hexlify

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
            return [chr(int(str[i:i + 2], 16)) for i in range(0, len(str), 2)]
        return None

    def __sendbytes__(self, command, bytes=None):
        if bytes:
            bytes = [chr(0xDD), chr(command)] + bytes + [crc.CRC8(bytes), chr(0xDE)]
        else:
            bytes = [chr(0xDD), chr(command), chr(0x00), chr(0xDE)]

        self.port.write(chr(0xDD))
        time.sleep(0.2)
        self.port.write(bytes)
        return self.port.read(1000)

    def __sendstr__(self, command, data=None):
        bytes = self.__strtobytes__(data)
        return self.__sendbytes__(command, bytes)

    def get_id(self):
        data = self.__sendstr__(0x09)
        if data == '':
            return 0
        message = data[3:6]
        mcrc = data[6]
        if crc.CRC8(message) == mcrc:
            return hexlify(message)
        return 0

    def transmit_buffer_size(self):
        data = self.__sendstr__(0x21)
        if data == '':
            return 0
        message = data[2]
        mcrc = data[3]
        if crc.CRC8(message) == mcrc:
            return int(hexlify(message), 16)
        return 0

    def echo(self, data):
        echoed = self.__sendstr__(0x00, data)
        message = echoed[2:2+len(data)/2]
        mcrc = echoed[2+len(data)/2]
        if crc.CRC8(message) == mcrc:
            return hexlify(message)
        return 0

    def transmit(self, data):
        response = self.__sendstr__(0x32, data)
        message = response[2]
        mcrc = response[3]
        if crc.CRC8(message) == mcrc:
            if ord(message) == 0:
                return True
            return False
        return False

    def config_mode(self, rw, receive_mode, mack_mode,
                    tx_phy_channel, rx_phy_channel,
                    tx_pwr, num_of_retries):

        return self.__sendbytes__(0x40, [rw, receive_mode, mack_mode, tx_phy_channel,
                                        rx_phy_channel, tx_pwr, num_of_retries])

    def config_handshake(self, rw, handshake_mode, mack_mode):

        return self.__sendbytes__(0x40, [rw, handshake_mode, mack_mode])

    def config_maxlen(self, rw, handshake_mode, mack_mode):

        return self.__sendbytes__(0x40, [rw, handshake_mode, mack_mode])
