# 指令结构
```json
{
  "IP": "192.168.1.200",
  "Port": 8888,
  "Card": "1394_CHR35251",
  "Data": {
    "ID": 1,
    "Length": "Int (1 byte) = 30*n + 18*m + k + 3",
    
    "ImageTargets": {
      "count": "Int (1 byte)",
      "item_size": 30,
      "items": [
        {
          "ImageTarget_id": "Int (1 byte)",
          "Type": "Int (1 byte)",
          "ImageTarget_distance_m": "Double (4 bytes)",
          "ImageTarget_azimuth_deg": "Double (4 bytes)",
          "Frequency_hz": "Double (4 bytes)",
          "Distance_30ms_m": "Double (4 bytes)",
          "Azimuth_30ms_deg": "Double (4 bytes)",
          "Speed_m_s": "Double (4 bytes)",
          "Direction_deg": "Double (4 bytes)"
        }
      ]
    },

    "RadarTargets": {
      "count": "Int (1 byte)",
      "item_size": 18,
      "items": [
        {
          "RadarTarget_id": "Int (1 byte)",
          "RadarTarget_distance_m": "Double (4 bytes)",
          "RadarTarget_azimuth_deg": "Double (4 bytes)",
          "Rcs_db": "Double (4 bytes)",
          "Velocity_m_s": "Double (4 bytes)"
        }
      ]
    },

    "FireControlRequests": {
      "count": "Int (1 byte)",
      "item_size": 1,
      "items": [
        {
          "Requested_target_id": "Int (1 byte)"
        }
      ]
    }
  }
}

```