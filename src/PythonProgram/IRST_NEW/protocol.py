import struct
import json

class Protocol:
    # Types
    # c: char (1), b: signed char (1), B: unsigned char (1)
    # h: short (2), H: unsigned short (2)
    # i: int (4), I: unsigned int (4)
    # f: float (4), d: double (8)
    
    # Output Packet Constants (Simulator -> Internal)
    OUTPUT_HEADER = 0xAA55
    
    # Input Packet Constants (Internal -> Simulator)
    INPUT_HEADER = 0xAA55

    @staticmethod
    def pack_output(config, targets):
        """
        Pack Output parameters (Simulator -> Internal)
        """
        # Global fields
        detect_range = float(config.get("DetectRange_m", 10000))
        ang_res = float(config.get("AngularResolution_deg", 0.1))
        range_acc = float(config.get("RangeAccuracy_m", 5))
        refresh_rate = float(config.get("RefreshRate_Hz", 50))
        
        num_targets = len(targets)
        
        # Calculate length: 
        # Global(16) + Num(1) + Targets(N * 51) + FOV(4)
        # Note: Length field itself is usually length of "Effective Data" (after Length field) or full packet. 
        # README says "后续有效数据长度" (Length of subsequent valid data).
        # So Length = Size of everything after 'Length' field.
        
        target_block_size = 51
        payload_len = 16 + 1 + (num_targets * target_block_size) + 4
        
        # Header (2), Msg (1), Len (2)
        # Assuming Msg Type is configurable or fixed. Let's use 1.
        msg_type = 1 
        
        buffer = struct.pack('<HBH', Protocol.OUTPUT_HEADER, msg_type, payload_len)
        
        # Global
        buffer += struct.pack('<ffff', detect_range, ang_res, range_acc, refresh_rate)
        buffer += struct.pack('<B', num_targets)
        
        for t in targets:
            # Target fields
            # ID(1), Type(1), Res(2), W(2), H(2), Depth(1), Fmt(1), Dist(4), Az(4), El(4), 
            # Vel(4), Laser(4), Conf(4), Threat(1), Stealth(1), Res2(2), Track(1), AzMiss(4), ElMiss(4), TgtAz(4)
            
            buffer += struct.pack('<BBHHHBBffffffBBHBfff',
                t.get("id", 0),
                t.get("type", 0),
                0, # Reserved
                t.get("width", 64),
                t.get("height", 64),
                t.get("depth", 8),
                t.get("format", 0),
                t.get("distance", 0),
                t.get("azimuth", 0),
                t.get("elevation", 0),
                t.get("velocity", 0),
                t.get("laser_range", 0),
                t.get("confidence", 0.9),
                t.get("threat", 0),
                t.get("stealth", 0),
                0, # Reserved2
                t.get("track_cmd", 0),
                t.get("az_miss", 0),
                t.get("el_miss", 0),
                t.get("target_az", 0)
            )
            
        # FOV Center
        fov_center = float(config.get("FOVCenterAzimuth_deg", 0))
        buffer += struct.pack('<f', fov_center)
        
        return buffer

    @staticmethod
    def unpack_input(data):
        """
        Unpack Input parameters (Internal -> Simulator)
        Returns a dict
        """
        if len(data) < 5:
            return None
            
        header, msg_type, length = struct.unpack('<HBH', data[:5])
        
        if header != Protocol.INPUT_HEADER:
            return None
            
        # Verify length if possible, but for streaming we might just process
        expected_len = 5 + length
        if len(data) < expected_len:
            return None # Incomplete
            
        # Payload starts at 5
        offset = 5
        
        # Lon(8), Lat(8)
        lon, lat = struct.unpack('<dd', data[offset:offset+16])
        offset += 16
        
        # Num(1), Max(1)
        num_targets, max_targets = struct.unpack('<BB', data[offset:offset+2])
        offset += 2
        
        targets = []
        target_size = 37 # Calculated previously
        
        for _ in range(num_targets):
            # ID(1), Type(1), Dist(4), Az(4), El(4), Vel(4), Conf(4), Threat(1), Stealth(1), Track(1), AzMiss(4), ElMiss(4), TgtAz(4)
            tid, ttype, dist, az, el, vel, conf, threat, stealth, track, az_miss, el_miss, tgt_az = struct.unpack(
                '<BBfffffBBBfff', data[offset:offset+37]
            )
            
            targets.append({
                "id": tid, "type": ttype, "distance": dist, "azimuth": az, "elevation": el,
                "velocity": vel, "confidence": conf, "threat": threat, "stealth": stealth,
                "track_cmd": track, "az_miss": az_miss, "el_miss": el_miss, "target_az": tgt_az
            })
            offset += 37
            
        # FOV Center (4)
        fov_center = struct.unpack('<f', data[offset:offset+4])[0]
        
        return {
            "header": header,
            "msg_type": msg_type,
            "lon": lon,
            "lat": lat,
            "targets": targets,
            "fov_center": fov_center
        }

