import yaml
from pathlib import Path
from .datatypes import Device
from typing import List

CFG_PATH = Path(__file__).with_suffix('').parent / 'data' / 'family_config.yaml'

def load_devices() -> List[Device]:
    cfg = yaml.safe_load(CFG_PATH.read_text())
    out = []
    for fam, body in cfg['families'].items():
        for d in body['devices']:
            out.append(Device(family=fam, **d, adults=body.get('adults', 2)))
    return out

def adults_by_family(devices):
    res = {}
    for d in devices:
        res.setdefault(d.family, d.adults)
    return res