import os
import sys
import winreg

def register_browser_extension():
    ext_dir = os.path.abspath(r"F:\UniGrab\extension")
    manifest_path = os.path.join(ext_dir, "manifest.json")
    
    if not os.path.exists(manifest_path):
        print("Extension folder not found!")
        return

    # Registry keys for Edge and Chrome external extensions
    registry_targets = [
        (winreg.HKEY_CURRENT_USER, r"Software\Google\Chrome\PreferenceMACs\Default\extensions"),
        (winreg.HKEY_CURRENT_USER, r"Software\Policies\Google\Chrome\ExtensionInstallAllowlist"),
        (winreg.HKEY_CURRENT_USER, r"Software\Policies\Microsoft\Edge\ExtensionInstallAllowlist"),
    ]

    print("Extension ready at:", ext_dir)
    print("Edge/Chrome can load this via Developer Mode or Group Policy.")

if __name__ == "__main__":
    register_browser_extension()
