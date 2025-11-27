"""ICD 导入与解析占位。"""

from __future__ import annotations

from typing import Dict, Any
from pathlib import Path
import json
import yaml


def load_icd(path: Path) -> Dict[str, Any]:
    """加载 ICD 文件（JSON/YAML）。"""

    try:
        if path.suffix.lower() in {".yaml", ".yml"}:
            return yaml.safe_load(path.read_text(encoding="utf-8"))
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
