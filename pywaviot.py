from waviotmodem import WaviotModem

testmodem = WaviotModem('COM5')

print (testmodem.get_id())
print (testmodem.transmit('ABCD'))
print (testmodem.transmit_buffer_size())