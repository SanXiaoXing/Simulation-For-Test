import socket
import struct
import time
from das_protocol import DASProtocol

def run_server():
    local_ip = "127.0.0.1"
    local_port = 6000 # DAS sends here
    remote_ip = "127.0.0.1"
    remote_port = 6001 # DAS listens here
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((local_ip, local_port))
    print(f"DAS Control Server listening on {local_ip}:{local_port}")
    
    seq = 0
    
    # Define a simple truth target list to send to DAS (Input Param)
    # TgtNum(1) + Loop(ID, Az, El, Range)
    input_targets = [
        {'id': 101, 'azimuth': 45.0, 'elevation': 10.0, 'range': 5000.0}
    ]
    
    while True:
        try:
            # 1. Receive Output from DAS
            try:
                sock.settimeout(0.1)
                data, addr = sock.recvfrom(65535)
                # Parse header to check validity
                if len(data) > 4:
                    header = struct.unpack('<H', data[:2])[0]
                    if header == 0xAA55:
                        # Extract basic info
                        # Header(2)+Msg(1)+Len(2)+Seq(2)
                        # Fixed1(7) + Sub(3*N) + Sensor(7) + Img(Len) + TgtNum(1) ...
                        # It's hard to unpack fully without knowing dynamic lengths,
                        # but we can just check length
                        pass
                        # print(f"Received {len(data)} bytes from DAS")
            except socket.timeout:
                pass
            
            # 2. Send Input Control to DAS
            # Header(2)+Msg(1)+Len(2)+Seq(2)
            # Scenario(1)+Cmd(1)+Sys(1)+Task(1)+State(1)+TgtNum(1)
            # Targets...
            # EW(1)
            
            tgt_num = len(input_targets)
            payload_len = 6 + (tgt_num * 13) + 1
            
            buffer = struct.pack('<HBH H', 0xAA55, 1, payload_len, seq)
            
            # Scenario=1, Cmd=1, Sys=2, Task=1, State=1, TgtNum=1
            buffer += struct.pack('<BBBBBB', 1, 1, 2, 1, 1, tgt_num)
            
            for t in input_targets:
                buffer += struct.pack('<Bfff', t['id'], t['azimuth'], t['elevation'], t['range'])
                
            buffer += struct.pack('<B', 0) # EW
            
            sock.sendto(buffer, (remote_ip, remote_port))
            seq = (seq + 1) % 65535
            
            time.sleep(1.0) # Send control commands every 1s
            
        except Exception as e:
            print(e)
            time.sleep(1)

if __name__ == "__main__":
    run_server()
