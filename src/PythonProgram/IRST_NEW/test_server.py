import socket
import struct

def run_server():
    local_ip = "127.0.0.1"
    local_port = 5000 # Simulator sends to here
    remote_ip = "127.0.0.1"
    remote_port = 5001 # Simulator listens here
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((local_ip, local_port))
    print(f"Dummy Internal Sim listening on {local_ip}:{local_port}")
    
    while True:
        try:
            data, addr = sock.recvfrom(4096)
            # Unpack Output packet (Simulator -> Internal)
            # Header(2), Msg(1), Len(2)
            if len(data) < 5: continue
            header = struct.unpack('<H', data[:2])[0]
            if header != 0xAA55: continue
            
            # Skip parsing details, just generate Input packet based on it
            # We need to extract target count and targets to echo them back
            
            # Output structure:
            # Header(2)+Msg(1)+Len(2)+Global(16)+Num(1)
            offset = 21 + 1
            if len(data) <= offset: continue
            num_targets = data[21]
            
            # Extract targets from Output packet
            # Target block size in Output is 51
            # Input block size is 37
            
            output_targets = []
            current_offset = 22
            for _ in range(num_targets):
                if current_offset + 51 > len(data): break
                t_data = data[current_offset : current_offset+51]
                # ID is at byte 0
                # Dist is at byte 7+4=11? No.
                # Output Target Struct:
                # ID(1), Type(1), Res(2), W(2), H(2), Depth(1), Fmt(1), Dist(4)...
                # 1+1+2+2+2+1+1 = 10 bytes before Dist.
                tid = t_data[0]
                ttype = t_data[1]
                dist = struct.unpack('<f', t_data[10:14])[0]
                az = struct.unpack('<f', t_data[14:18])[0]
                el = struct.unpack('<f', t_data[18:22])[0]
                vel = struct.unpack('<f', t_data[22:26])[0]
                # ...
                output_targets.append({
                    "id": tid, "type": ttype, "dist": dist, "az": az, "el": el, "vel": vel
                })
                current_offset += 51
                
            # Construct Input Packet
            # Header(2)+Msg(1)+Len(2)
            # Lon(8)+Lat(8)
            # Num(1)+Max(1)
            # Targets (37 bytes each)
            # FOV(4)
            
            payload_len = 16 + 2 + num_targets * 37 + 4
            resp = struct.pack('<HBH', 0xAA55, 2, payload_len)
            resp += struct.pack('<dd', 116.0, 40.0) # Lon, Lat
            resp += struct.pack('<BB', num_targets, 10) # Num, Max
            
            for t in output_targets:
                # ID(1), Type(1), Dist(4), Az(4), El(4), Vel(4), Conf(4), Threat(1), Stealth(1), Track(1), AzMiss(4), ElMiss(4), TgtAz(4)
                # We echo back with some noise or processed data
                resp += struct.pack('<BBfffffBBBfff',
                    t['id'], t['type'], t['dist'], t['az'], t['el'], t['vel'],
                    0.9, 1, 0, 0, 0.0, 0.0, t['az']
                )
            
            resp += struct.pack('<f', 0.0) # FOV Center
            
            sock.sendto(resp, (remote_ip, remote_port))
            # print(f"Echoed {num_targets} targets to {remote_port}")
            
        except Exception as e:
            print(e)

if __name__ == "__main__":
    run_server()
