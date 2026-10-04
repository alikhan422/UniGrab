import os
import sys
import json

if sys.platform == "win32":
    import winreg


def register(extension_id: str):
    base_dir = os.path.abspath(os.path.dirname(__file__))
    manifest_path = os.path.join(base_dir, "native_host", "com.omnistream.studio.json")
    script_path = os.path.join(base_dir, "native_host", "host_bridge.py")

    # utf-8-sig handles UTF-8 BOM automatically
    with open(manifest_path, "r", encoding="utf-8-sig") as f:
        data = json.load(f)

    data["allowed_origins"] = [f"chrome-extension://{extension_id}/"]
    data["path"] = script_path

    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    if sys.platform == "win32":
        targets = [
            r"Software\Google\Chrome\NativeMessagingHosts\com.omnistream.studio",
            r"Software\Microsoft\Edge\NativeMessagingHosts\com.omnistream.studio"
        ]
        for t in targets:
            try:
                with winreg.CreateKey(winreg.HKEY_CURRENT_USER, t) as key:
                    winreg.SetValueEx(key, "", 0, winreg.REG_SZ, manifest_path)
                print(f"[Registry] Configured: HKCU\\{t}")
            except Exception as e:
                print(f"[Registry Error] Failed on {t}: {e}")
    else:
        print("[Registration] Manifest updated. Link this manifest into your browser's NativeMessagingHosts folder.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python register_host.py ")
    else:
        register(sys.argv[1])