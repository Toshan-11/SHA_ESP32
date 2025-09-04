import subprocess
import re

def get_esp_ip():
    cmd = "arp -a"
    output = subprocess.check_output(cmd, shell=True).decode()
    devices = []
    for line in output.splitlines():
        match = re.search(r"(\d+\.\d+\.\d+\.\d+)\s+([\w-]{17}|[a-fA-F0-9:]{17}|[a-fA-F0-9:]{2}(?::[a-fA-F0-9]{2}){5})", line)
        if match:
            ip = match.group(1)
            if ip.startswith("192") and not any([ip.endswith(i) for i in ["255","254"]]):
                devices.append(ip)
    return devices

if __name__ == "__main__":
    print(get_esp_ip())
