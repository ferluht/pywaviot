from waviotmodem import WaviotModem
from appJar import gui
import re
from time import sleep
from binascii import hexlify
import os

answer_pattern = re.compile("FWUPD-[0-9a-fA-F]{6}")
ack_pattern = re.compile("PKTOK-[0-9a-fA-F]{6}-[0-9a-fA-F]{1,2}")

firmware_path = "no firmware selected"
fw_file = None
fw_block_it = 1
fw_size = 0

RETRY_LIMIT = 10
FW_CHUNK_SIZE = 60

modem = None

main = None
popup = None

fw_uploaded_size = 0
discover_percent = 0

select = True

waviot = WaviotModem('COM3')
# waviot.__sendbytes__(0x01, [0x01, 0xDD, 0x02, 0xDE])
print (waviot.get_id())
waviot.enable_fastDL()
waviot.set_dl(0x6FB26F)

# while 1:
#     global waviot
#     waviot.transmit_fastDL(chr(0x03)+chr(51)+'aa')
#     sleep(0.1)
#     m = waviot.receive()
#     if m:
#         print(m)

def getSize(fileobject):
    fileobject.seek(0,2) # move the cursor to the end of the file
    size = fileobject.tell()
    return size

def display_path(path, length):
    if len(path) > length:
        halflen = (length - 3)/2
        return path[0:halflen] + '...' + path[-halflen:len(path)]
    return path

def choose_file(btnName):
    global firmware_path, main
    firmware_path = main.openBox(title="Choose the firmware", dirName=None, fileTypes=[('binary', '*.bin'), ('binary', '*.hex')], asFile=False)
    main.setLabel("fw_path", display_path(firmware_path, 20))
    fw_file = open(firmware_path, 'rb')

def select_all_modems(btnName):
    global main, select
    for modem in modems:
        main.setOptionBox("available modem list", modem, value=select)
    select = not select
    if (select):
        main.setButton("select all", "select all")
    else:
        main.setButton("select all", "deselect all")

def start_main_window():
    global firmware_path, main
    main = gui()
    main.addLabel("fw_path", display_path(firmware_path, 20), 0, 0)
    main.addButtons(["Open firmware"], choose_file, 0, 1)
    main.addButtons(["select all"], select_all_modems, 3, 1)
    main.addLabelEntry("Modems:", 1, 0)
    main.addButtons(["     Discover     "], discover, 1, 1)
    main.addButtons(["        Flash        "], flash, 2, 1)
    main.addLabelSecretEntry("Password:", 2, 0)
    # main.addTickOptionBox("available modem list", modem, 3, 0)
    main.go()

def end_upload():
    global waviot
    waviot.transmit_fastDL(chr(0x02))
    popup.infoBox("complete", "Upload completed for modems:")
    popup.stop()
    start_main_window()

def broadcast_cmd(cmdlist, data=None, ack_pattern=None, WATRANSMIT=0, WFRETRY=0.1):
    buffer = ''
    for cmd in cmdlist:
        buffer += chr(cmd)
    buffer += data

    waviot.transmit_fastDL(buffer)
    sleep(WATRANSMIT)
    acked = False

    for i in range(3):
        sleep(WFRETRY)
        ack = waviot.receive()
        if ack and ack_pattern.match(ack):
            id = ack[6:12]
            if id == modem:
                acked = True
                ack = id
            break

    return ack, acked

def upload_firmware():
    global FW_CHUNK_SIZE, waviot, modem, popup, fw_uploaded_size, fw_file, fw_size, fw_block_it, ack_pattern
    popup.setMeter("progress", float(fw_uploaded_size)/float(fw_size)*100)

    buff = fw_file.read(FW_CHUNK_SIZE)

    for i in range(RETRY_LIMIT):
        id, ack = broadcast_cmd([0x03, fw_block_it,], buff, ack_pattern=ack_pattern)
        if ack == True:
            break
        print("Retry")

    if not ack:
        if id:
            print("flashing modem " + id + " failed on block " + str(fw_block_it))
        else:
            print("nobody acked")
        popup.stop()
        start_main_window()

    print (id + ' acked on ' + str(fw_block_it))

    fw_block_it += 1

    fw_uploaded_size += FW_CHUNK_SIZE;

    if fw_uploaded_size >= fw_size:
        end_upload()

def flash(btnName):
    global firmware_path, main, popup, fw_uploaded_size, fw_file, fw_size
    if firmware_path == "no firmware selected":
        main.errorBox("no_fw_choosen", "choose firmware")
        return
    fw_file = open(firmware_path, 'rb')
    fw_size = getSize(fw_file)
    fw_file = open(firmware_path, 'rb')
    main.stop()

    fw_uploaded_size = 0
    popup = gui()
    popup.setFont(12)
    popup.addMessage("mess", "flashing...")
    popup.addMeter("progress")
    popup.registerEvent(upload_firmware)
    popup.go()

def refresh_modems():
    global waviot, popup, discover_percent, modem
    discover_percent += 1.5
    popup.setMeter("modem_discovering", discover_percent)

    if discover_percent > 100:
        # popup.unregisterEvent(refresh_modems)
        popup.stop()
        start_main_window()
        return
    s = waviot.receive()
    if not s:
        return
    if answer_pattern.match(s):
        id = s[-6:]
        if not id == modem:
            print ("found: " + id)
            modem = id
            # popup.unregisterEvent(refresh_modems)
            popup.stop()
            start_main_window()

def discover(btnName):
    global main, popup, modems, discover_percent, waviot

    waviot.transmit_fastDL(chr(0x04))
    main.stop()
    discover_percent = 0
    popup = gui()
    modems = []
    popup.addMeter("modem_discovering")
    popup.registerEvent(refresh_modems)
    popup.go()
    start_main_window()

start_main_window()
# print (testmodem.set_dl(0x6FB26F))