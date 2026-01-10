import struct
import numpy as np

class DASProtocol:
    HEADER = 0xAA55
    
    @staticmethod
    def pack_output(seq, state, sensor_config, image_data, targets, fov_info):
        """
        Pack Output parameters (DAS -> Control)
        """
        # Fixed Header: Header(2)+Msg(1)+Len(2)+Seq(2)
        # Fixed Payload 1: Cmd(1)+Sys(1)+Task(1)+State(1)+Overlay(1)+Render(1)+SubNum(1)
        # SubModules: Loop
        # Sensor: SensorID(1)+W(2)+H(2)+Depth(1)+Fmt(1)
        # Image: Data
        # Targets: Num(1) + Loop
        # Tail: EW(1)+Fake(1)+FOVAz(4)+FOVEl(4)+FOVW(4)+FOVH(4)
        
        # Mock values for fields not passed in
        cmd = state.get('ControlCmd', 0)
        sys_mode = state.get('SystemMode', 0)
        task_mode = state.get('TaskMode', 0)
        sim_state = state.get('SimulationState', 0)
        overlay = state.get('OverlayEnable', 0)
        render = state.get('RenderMode', 0)
        
        # SubModules (Mocking 2 submodules)
        sub_modules = [
            {'id': 1, 'state': 1, 'enable': 1},
            {'id': 2, 'state': 1, 'enable': 1}
        ]
        sub_num = len(sub_modules)
        
        # Sensor Info
        sensor_id = sensor_config.get('SensorID', 0)
        w = sensor_config.get('ImageWidth', 64)
        h = sensor_config.get('ImageHeight', 64)
        depth = sensor_config.get('PixelDepth', 8)
        fmt = sensor_config.get('ImageFormat', 0)
        
        # Image Data Handling
        # Ensure image data matches W*H
        # For simulation, we generate dummy noise if not provided
        if image_data is None:
            img_bytes = bytes([0] * (w * h)) # 8-bit grayscale
        else:
            img_bytes = image_data # Expecting bytes
            
        # Targets
        tgt_num = len(targets)
        
        # Calculate Length
        # Fixed1(7) + Sub(3*N) + Sensor(7) + Img(Len) + TgtNum(1) + Tgt(13*M) + Tail(18)
        payload_len = 7 + (sub_num * 3) + 7 + len(img_bytes) + 1 + (tgt_num * 13) + 18
        
        # Pack Header
        buffer = struct.pack('<HBH H', DASProtocol.HEADER, 2, payload_len, seq)
        
        # Fixed Payload 1
        buffer += struct.pack('<BBBBBBB', cmd, sys_mode, task_mode, sim_state, overlay, render, sub_num)
        
        # SubModules
        for sub in sub_modules:
            buffer += struct.pack('<BBB', sub['id'], sub['state'], sub['enable'])
            
        # Sensor Info
        buffer += struct.pack('<BHHBB', sensor_id, w, h, depth, fmt)
        
        # Image Data
        buffer += img_bytes
        
        # Targets
        buffer += struct.pack('<B', tgt_num)
        for t in targets:
            # ID(1), Az(4), El(4), Range(4)
            buffer += struct.pack('<Bfff', 
                t.get('id', 0), 
                t.get('azimuth', 0), 
                t.get('elevation', 0), 
                t.get('range', 0)
            )
            
        # Tail
        buffer += struct.pack('<BBffff',
            state.get('EWInterferenceLevel', 0),
            state.get('FakeTargetFlag', 0),
            fov_info.get('center_az', 0),
            fov_info.get('center_el', 0),
            fov_info.get('width', 120),
            fov_info.get('height', 90)
        )
        
        return buffer

    @staticmethod
    def unpack_input(data):
        """
        Unpack Input parameters (Control -> DAS)
        """
        if len(data) < 7: return None
        
        header, msg_type, length, seq = struct.unpack('<HBH H', data[:7])
        if header != DASProtocol.HEADER: return None
        
        offset = 7
        # Scenario(1), Cmd(1), Sys(1), Task(1), State(1), TgtNum(1)
        scenario, cmd, sys_mode, task_mode, sim_state, tgt_num = struct.unpack('<BBBBBB', data[offset:offset+6])
        offset += 6
        
        targets = []
        for _ in range(tgt_num):
            # ID(1), Az(4), El(4), Range(4)
            tid, az, el, rng = struct.unpack('<Bfff', data[offset:offset+13])
            targets.append({
                'id': tid, 'azimuth': az, 'elevation': el, 'range': rng
            })
            offset += 13
            
        # EW(1)
        if offset < len(data):
            ew = struct.unpack('<B', data[offset:offset+1])[0]
        else:
            ew = 0
            
        return {
            'seq': seq,
            'scenario': scenario,
            'cmd': cmd,
            'sys_mode': sys_mode,
            'task_mode': task_mode,
            'sim_state': sim_state,
            'targets': targets,
            'ew': ew
        }
