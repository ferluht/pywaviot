from waviotmodem import WaviotModem

modem = WaviotModem('COM3')
# wakeup from sleep mode
modem.wakeup()
# print id of modem
print (modem.get_id())
# transmit 'payload'
modem.transmit('payload')
# receive downlink message
while(1):
    mes = modem.receive()
    if mes:
        print (mes)
# set FastDL
modem.set_fastDL()