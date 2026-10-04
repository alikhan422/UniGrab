import os
import glob

def get_logo_path():
    base = os.path.dirname(os.path.abspath(__file__))
    patterns = [
        os.path.join(base, "assets", "logo.*"),
        os.path.join(base, "logo.*"),
        os.path.join(base, "*logo*.*")
    ]
    for pattern in patterns:
        matches = glob.glob(pattern)
        for m in matches:
            if m.lower().endswith(('.png', '.jpg', '.jpeg', '.ico')):
                return os.path.abspath(m)
    return None
