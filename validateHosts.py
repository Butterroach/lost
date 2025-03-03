import ipaddress
from urllib.parse import urlparse


def isValidIP(ip):
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False


def isValidHostname(hostname):
    parsed = urlparse(f"//{hostname}")

    if not parsed.hostname:
        return False

    if parsed.path or parsed.params or parsed.query or parsed.fragment:
        return False

    return parsed.hostname == hostname


def validateHostsFile(data):
    lines = data.splitlines()
    for line in lines:
        line = line.split("#")[0].strip()

        if not line:
            continue

        parts = line.split()

        if len(parts) < 2:
            return False

        ip = parts[0]
        if not isValidIP(ip):
            return False

        for hostname in parts[1:]:
            if not isValidHostname(hostname):
                return False

    return True
