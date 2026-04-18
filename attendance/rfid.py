from smartcard.System import readers


def read_card():
    r = readers()
    reader = r[0]
    connection = reader.createConnection()
    connection.connect()

    GET_UID = [0xFF, 0xCA, 0x00, 0x00, 0x00]

    data, sw1, sw2 = connection.transmit(GET_UID)
    uid = ''.join(format(x, '02X') for x in data)

    return uid