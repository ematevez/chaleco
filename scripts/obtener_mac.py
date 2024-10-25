import uuid

def obtener_mac():
    mac = hex(uuid.getnode()).replace('x', '').upper()
    mac = ':'.join(mac[i:i+2] for i in range(0, 12, 2))
    return mac

print(obtener_mac())


#04:7C:16:AD:6A:14   Notebook gammer