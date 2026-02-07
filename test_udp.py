import socket
import struct

UDP_IP = "127.0.0.1"
UDP_PORT = 5000

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))

print(f"Listening on UDP {UDP_IP}:{UDP_PORT}...")

while True:
    data, addr = sock.recvfrom(1024)
    
    # We expect 13 bytes: 4 (ID) + 1 (DLC) + 8 (Data)
    if len(data) == 13:
        # Unpack the C struct: I = uint32, B = uint8, 8s = 8 bytes
        can_id, dlc, payload = struct.unpack("<IB8s", data)
        
        # Parse payload
        volt_hi = payload[0]
        volt_lo = payload[1]
        temp = payload[2]
        status = payload[3]
        
        voltage = (volt_hi << 8) | volt_lo
        
        print(f"RX CAN ID: 0x{can_id:X} | Voltage: {voltage}mV | Temp: {temp}C | Status: {status}")