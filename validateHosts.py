import ipaddress
from urllib.parse import urlparse
from typing import Tuple, Optional, List


def isValidIP(ip) -> Tuple[bool, bool]:
    """
    Returns a tuple of two booleans.

    The first boolean indicates whether the input is a valid IP address.
    The second boolean indicates whether the IP is NOT a null ip.
    """
    try:
        ip = ipaddress.ip_address(ip)
        return True, not (ip.is_reserved or ip.is_private)
    except ValueError:
        return False, False


def isValidHostname(hostname) -> bool:
    """
    This returns whether the given hostname is valid for use in a hosts file or not.
    """
    parsed = urlparse(f"//{hostname}")

    if not parsed.hostname:
        return False

    if parsed.path or parsed.params or parsed.query or parsed.fragment:
        return False

    return parsed.hostname == hostname


def validateHostsFile(data) -> Tuple[bool, Optional[List[str]]]:
    """
    This takes a hosts file (in its entirety) and returns a boolean, and optionally, a list of strings.

    The boolean is True if the hosts file is valid, and False otherwise.

    The list of strings will only be provided IF and ONLY IF the hosts file could POTENTIALLY be dangerous (and is valid)!!!!
    The strings provided will be entries in the provided hosts file that don't point to null/reserved IPs,
    and could potentially be used to redirect traffic to malicious sites.

    **User should be notified of those malicious entries if they are found!!!!!!**
    """
    lines = data.splitlines()
    dangerous = []
    for line in lines:
        line = line.split("#")[0].strip()

        if not line:
            continue

        parts = line.split()

        if len(parts) < 2:
            return (False,)

        ip = parts[0]
        isIpValid = isValidIP(ip)
        if not isIpValid[0]:
            return (False,)

        for hostname in parts[1:]:
            if not isValidHostname(hostname):
                return (False,)

        if isIpValid[1]:
            dangerous.append(line)  # POTENTIALLY DANGEROUS ENTRY

    return (True,) if not dangerous else (True, dangerous)
