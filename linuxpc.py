#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ITAM Asset Inventory Console (Linux Edition - Tích hợp pass root trực tiếp)
By Hachihi.vn - Support Hải Hoàng : 09-1800-1944
"""

import os
import sys
import json
import socket
import platform
import re
import shutil
import subprocess
import urllib.request
import urllib.error
from datetime import datetime

# ================== CẤU HÌNH ==================
WEBHOOK_URL = "https://kiemkepc.haihoang-hch.workers.dev"
TOKEN = "0918001944"
USER_NAME = "Auto HCH"
DEPARTMENT = "IT System"
KIEM_KE_ID = "AutoSystem"

# ĐIỀN MẬT KHẨU ROOT/SUDO CỦA BẠN VÀO ĐÂY (Ví dụ: "123456" hoặc "P@ssword")
SUDO_PASSWORD = "Hch@!Muaantam2026"

_log_lines = []


def log(message):
    _log_lines.append("[{0}] {1}".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), message))


def run_cmd(cmd, timeout=5):
    """Chạy lệnh shell, tự động truyền pass root nếu chưa chạy bằng quyền root."""
    try:
        is_str = isinstance(cmd, str)
        
        # Nếu chưa chạy bằng quyền root (euid != 0) và có cấu hình mật khẩu
        if os.geteuid() != 0 and SUDO_PASSWORD != "DIEN_PASS_ROOT_CVA_BAN_VAI_DAY":
            if is_str:
                clean_cmd = cmd[5:] if cmd.startswith("sudo ") else cmd
                full_cmd = f"echo '{SUDO_PASSWORD}' | sudo -S {clean_cmd}"
            else:
                clean_cmd = cmd[1:] if (len(cmd) > 0 and cmd[0] == "sudo") else cmd
                full_cmd = ["sudo", "-S"] + clean_cmd
            
            p = subprocess.run(
                full_cmd,
                shell=is_str,
                input=f"{SUDO_PASSWORD}\n" if not is_str else None,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                timeout=timeout,
                text=True,
            )
            return (p.stdout or "").strip()

        # Trường hợp đã là root hoặc không dùng sudo
        result = subprocess.run(
            cmd,
            shell=is_str,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=timeout,
            text=True,
        )
        return (result.stdout or "").strip()
    except Exception:
        return ""


def has_cmd(name):
    return shutil.which(name) is not None


# ================== CÁC LỆNH LẤY THÔNG TIN PHẦN CỨNG ==================

def get_manufacturer():
    out = run_cmd("sudo dmidecode -s baseboard-manufacturer")
    return out if out else "N/A"


def get_model():
    out = run_cmd("sudo dmidecode -s system-product-name")
    return out if out else "N/A"


def get_serial_number():
    out = run_cmd("sudo dmidecode -s system-serial-number")
    return out if out else "N/A"


def get_current_user():
    out = run_cmd("whoami")
    return out if out else (os.environ.get("USER") or "N/A")


def get_hostnamectl_info():
    data = {
        "Computer": "N/A",
        "Chassis": "N/A",
        "MachineID": "N/A",
        "OperatingSystem": "N/A",
        "HardwareVendor": "N/A",
        "FirmwareVersion": "N/A",
        "FirmwareDate": "N/A"
    }
    out = run_cmd("hostnamectl")
    if not out:
        return data

    for line in out.splitlines():
        if ":" in line:
            parts = line.split(":", 1)
            k = parts[0].strip().lower()
            v = parts[1].strip()
            if "static hostname" in k:
                data["Computer"] = v
            elif "chassis" in k:
                data["Chassis"] = v
            elif "machine id" in k:
                data["MachineID"] = v
            elif "operating system" in k:
                data["OperatingSystem"] = v
            elif "hardware vendor" in k:
                data["HardwareVendor"] = v
            elif "firmware version" in k:
                data["FirmwareVersion"] = v
            elif "firmware date" in k:
                data["FirmwareDate"] = v
    return data


def get_cpu_info():
    out = run_cmd("sudo dmidecode -s processor-version")
    return out if out else "N/A"


def get_ram_info():
    out = run_cmd('sudo dmidecode -t memory | egrep "Size:|Manufacturer:|Part Number:|Speed:|Configured Memory Speed:|Locator:"')
    return out if out else "N/A"


def get_gpu_info():
    out = run_cmd('lspci | grep -Ei "vga|3d|display"')
    return out if out else "N/A"


def get_drive_info():
    out = run_cmd("lsblk -d -o NAME,MODEL,SERIAL,SIZE,ROTA,TRAN,VENDOR")
    return out if out else "N/A"


def get_lan_ip_and_gateway():
    out = run_cmd("ip route")
    lan_ip = "N/A"
    gateway = "N/A"
    
    m_gw = re.search(r"default via (\S+)", out)
    if m_gw:
        gateway = m_gw.group(1)

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(1)
        s.connect(("8.8.8.8", 80))
        lan_ip = s.getsockname()[0]
        s.close()
    except Exception:
        pass

    return lan_ip, gateway


def get_connected_wifi_name():
    out = run_cmd("nmcli -t -f active,ssid dev wifi | grep '^yes:' | cut -d: -f2-")
    return out if out else "No WiFi"


def get_wan_ip_address():
    out = run_cmd("curl -s https://api.ipify.org")
    if out:
        return out
    try:
        req = urllib.request.Request("https://api.ipify.org", headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            return resp.read().decode("utf-8", "ignore").strip()
    except Exception:
        return "N/A"


def collect_hardware_data():
    hw = {}
    hctl = get_hostnamectl_info()
    lan_ip, gateway = get_lan_ip_and_gateway()

    hw["Manufacturer"] = get_manufacturer()
    hw["Model"] = get_model()
    hw["Serial Number"] = get_serial_number()
    hw["User"] = get_current_user()
    
    hw["Computer"] = hctl["Computer"]
    hw["Chassis"] = hctl["Chassis"]
    hw["MachineID"] = hctl["MachineID"]
    hw["OperatingSystem"] = hctl["OperatingSystem"]
    hw["HardwareVendor"] = hctl["HardwareVendor"]
    hw["FirmwareVersion"] = hctl["FirmwareVersion"]
    hw["FirmwareDate"] = hctl["FirmwareDate"]

    hw["CPU"] = get_cpu_info()
    hw["RAM_Details"] = get_ram_info()
    hw["GPU"] = get_gpu_info()
    hw["Disk Drives"] = get_drive_info()

    hw["LAN_IP"] = lan_ip
    hw["Gateway"] = gateway
    hw["WiFi"] = get_connected_wifi_name()
    hw["WAN_IP"] = get_wan_ip_address()

    return hw


# ================== PHẦN MỀM ==================


import os
import glob
import subprocess


def get_manually_installed_packages():
    """
    Lấy danh sách các gói được NGƯỜI DÙNG cài thủ công bằng apt/dpkg
    (apt-mark showmanual). Các gói là dependency hoặc cài sẵn theo ISO
    (được apt-mark auto đánh dấu) sẽ KHÔNG nằm trong danh sách này.
    Nếu hệ thống không dùng apt (không phải Debian/Ubuntu/Mint) sẽ trả về set rỗng.
    """
    try:
        result = subprocess.run(
            ["apt-mark", "showmanual"],
            capture_output=True, text=True, check=True
        )
        return set(result.stdout.split())
    except Exception:
        return set()


def get_package_priority(pkg_name, _cache={}):
    """
    Trả về Priority của gói dpkg: required/important/standard = gói lõi hệ điều hành
    (Ubuntu/Mint dùng các mức này cho phần mềm cài sẵn). optional/extra = thường
    là phần mềm cài thêm.
    """
    if pkg_name in _cache:
        return _cache[pkg_name]
    try:
        result = subprocess.run(
            ["dpkg-query", "-W", "-f=${Priority}", pkg_name],
            capture_output=True, text=True
        )
        priority = result.stdout.strip() if result.returncode == 0 else None
    except Exception:
        priority = None
    _cache[pkg_name] = priority
    return priority


def get_owning_package(desktop_file_path, _cache={}):
    """
    Tìm gói .deb nào sở hữu file .desktop này.
    Trả về None nếu không thuộc gói nào (thường gặp với app tự cài tay,
    AppImage, hoặc build từ source).
    """
    if desktop_file_path in _cache:
        return _cache[desktop_file_path]
    pkg = None
    try:
        result = subprocess.run(
            ["dpkg", "-S", desktop_file_path],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            pkg = result.stdout.split(":")[0].strip()
    except Exception:
        pass
    _cache[desktop_file_path] = pkg
    return pkg


def collect_software_data():
    software_list = []
    seen_names = set()

    # (thư mục, loại nguồn cài đặt)
    # Flatpak/Snap hầu như luôn là do người dùng chủ động cài thêm nên
    # không cần tra dpkg cho 2 loại này.
    app_dirs = [
        ("/usr/share/applications", "deb"),
        (os.path.expanduser("~/.local/share/applications"), "local"),
        ("/var/lib/flatpak/exports/share/applications", "flatpak"),
        (os.path.expanduser("~/.local/share/flatpak/exports/share/applications"), "flatpak"),
        ("/var/lib/snapd/desktop/applications", "snap"),
    ]

    # Category thuộc nhóm công cụ cấu hình hệ thống / driver / control panel
    system_categories = {
        "Settings", "HardwareSettings", "DesktopSettings", "System",
        "X-GNOME-Settings-Panel", "X-Cinnamon-Settings-Panel",
        "ConsoleOnly", "Screensaver",
    }

    # Blacklist theo tên: dùng làm lớp lọc dự phòng khi máy không có apt/dpkg
    # (ví dụ chạy trên distro khác) hoặc dpkg -S không tra ra được gói.
    name_blacklist = {
        "matrix", "character map", "thunderbird mail", "new presentation",
        "libreoffice", "chromium web browser", "rhythmbox", "document scanner",
        "drawing", "files", "disks", "image viewer", "warpinator",
        "document viewer", "web apps", "calculator", "new spreadsheet",
        "vim", "usb image writer", "usb stick formatter", "file renamer",
        "firefox web browser", "fonts", "screenshot", "hypnotix",
        "virtual keyboard", "celluloid", "notes", "new document",
        "color selection dialog", "calendar", "archive manager", "onboard",
        "library", "text editor", "pix", "new drawing", "transmission",
        "passwords and keys", "color", "account details", "timeshift",
        "accessibility", "system monitor", "welcome screen", "display",
        "software manager", "night light", "mouse and touchpad", "keyboard",
        "power statistics", "network", "login window", "actions",
        "graphics tablet", "printers", "applets", "software sources",
        "firewall configuration", "desktop", "gnome system monitor",
        "bluetooth manager", "preferred applications", "disk usage analyzer",
        "input method", "ibus preferences", "font selection",
        "power management", "online accounts", "system information",
        "backup tool", "notifications", "system administration",
    }

    manual_packages = get_manually_installed_packages()

    for app_dir, source_type in app_dirs:
        if not os.path.exists(app_dir):
            continue

        for desktop_file in glob.glob(os.path.join(app_dir, "*.desktop")):
            try:
                app_name = None
                is_visible = True
                is_setting = False

                with open(desktop_file, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("NoDisplay=true") or line.startswith("Hidden=true"):
                            is_visible = False
                            break
                        if line.startswith("Name=") and not app_name:
                            app_name = line.split("=", 1)[1]
                        elif line.startswith("Name[en]="):
                            app_name = line.split("=", 1)[1]
                        elif line.startswith("Categories="):
                            categories = set(line.split("=", 1)[1].split(";"))
                            if system_categories.intersection(categories) and "Utility" not in categories:
                                is_setting = True

                if not is_visible or is_setting or not app_name:
                    continue

                if app_name.lower() in name_blacklist:
                    continue

                # Chỉ áp dụng kiểm tra package cho app cài qua deb/apt
                if source_type == "deb":
                    pkg = get_owning_package(desktop_file)
                    if pkg:
                        priority = get_package_priority(pkg)
                        # required/important/standard => gói lõi hệ điều hành, loại bỏ
                        if priority in ("required", "important", "standard"):
                            continue
                        # Nếu tra được danh sách manual, chỉ giữ app thuộc gói cài thủ công
                        if manual_packages and pkg not in manual_packages:
                            continue
                    # Nếu không xác định được gói (vd: tự copy .desktop thủ công)
                    # thì vẫn giữ lại, coi như người dùng tự thêm.

                if app_name not in seen_names:
                    seen_names.add(app_name)
                    software_list.append({
                        "Name": app_name,
                        "Version": "Unknown",
                        "Size": "0",
                        "Architecture": "amd64",
                        "Source": source_type,
                    })
            except Exception:
                pass

    return software_list

        




# ================== THIẾT BỊ NGOẠI VI ==================

def collect_peripherals_data():
    items = []
    try:
        if os.path.isdir("/dev"):
            for dev in sorted(os.listdir("/dev")):
                if dev.startswith("video"):
                    dev_path = f"/dev/{dev}"
                    name = dev_path
                    if has_cmd("v4l2-ctl"):
                        out = run_cmd(f"v4l2-ctl -d {dev_path} --info 2>/dev/null | grep 'Card type' | cut -d: -f2")
                        if out:
                            name = out.strip()
                    items.append({"DeviceName": name, "Category": "Webcam"})
    except Exception:
        pass

    try:
        if has_cmd("lpstat"):
            out = run_cmd(["lpstat", "-p"])
            for line in out.splitlines():
                if line.startswith("printer"):
                    parts = line.split()
                    if len(parts) > 1:
                        items.append({"DeviceName": parts[1], "Category": "Máy in"})
    except Exception:
        pass

    return items


# ================== GỬI WEBHOOK ==================

def send_payload(url, payload_dict):
    try:
        data = json.dumps(payload_dict, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            method="POST",
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json"
            },
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            response_text = resp.read().decode("utf-8", "ignore")
            log("Phản hồi từ Server: " + response_text)
            return True
    except Exception as ex:
        log("Lỗi gửi Webhook: " + str(ex))
        return False


# ================== MAIN ==================

def main():
    log("=" * 50)
    log("BẮT ĐẦU CHƯƠNG TRÌNH KIỂM KÊ TÀI SẢN (LINUX)")

    hardware_data = {}
    software_list = []
    peripherals_list = []

    try:
        hardware_data = collect_hardware_data()
    except Exception as ex:
        log("[LỖI PHẦN CỨNG] " + str(ex))

    try:
        software_list = collect_software_data()
    except Exception as ex:
        log("[LỖI PHẦN MỀM] " + str(ex))

    try:
        peripherals_list = collect_peripherals_data()
    except Exception as ex:
        log("[LỖI THIẾT BỊ NGOẠI VI] " + str(ex))

    machine_name = socket.gethostname()
    serial_number = hardware_data.get("Serial Number", "N/A")

    payload_object = {
        "token": TOKEN,
        "userName": hardware_data.get("User", "N/A"),
        "department": DEPARTMENT,
        "machineName": machine_name,
        "serialNumber": serial_number,
        "kiemkeId": KIEM_KE_ID,
        "hardwareData": hardware_data,
        "softwareList": software_list,
        "peripheralsList": peripherals_list,
    }

    success = send_payload(WEBHOOK_URL, payload_object)
    if success:
        log("[SUCCESS] Gửi dữ liệu thành công.")
    else:
        log("[FAIL] Gửi dữ liệu thất bại.")


if __name__ == "__main__":
    main()
