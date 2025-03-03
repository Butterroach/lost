import app
import requests


def test_valid_hosts():
    HOSTS = """
# comment
#comment
 #coment
127.0.0.1       localhost
::1             localhost
192.168.1.10    example.com
192.168.1.11    test.local
10.0.0.2        example.org         #  comment
127.0.0.1       myapp.local myapp

192.168.100.100 dev.mywebsite.com
192.168.100.101 staging.mywebsite.com
192.168.0.2     www.example.com       www.example.net api.example.com
2001:0db8:85a3:0000:0000:8a2e:0370:7334    ipv6example.com


0.0.0.0         blockedwebsite.com
127.0.0.1       anotherexample.com
"""
    assert app.validateHostsFile(HOSTS)


def test_invalid_ipv4_hosts():
    HOSTS = """
256.255.255.255  localhost
::1              localhost
"""
    assert not app.validateHostsFile(HOSTS)


def test_invalid_ipv6_hosts():
    HOSTS = """
127.0.0.1 localhost
:1        localhost
"""
    assert not app.validateHostsFile(HOSTS)


def test_invalid_syntax():
    HOSTS = """
google.com 0.0.0.0
"""
    assert not app.validateHostsFile(HOSTS)


def test_empty_hosts():
    HOSTS = ""
    assert app.validateHostsFile(HOSTS)  # this should be valid!


def test_hagezi_ultimate_uncompressed_hosts():
    # time for a real test!
    HOSTS = requests.get(
        "https://raw.githubusercontent.com/hagezi/dns-blocklists/main/hosts/ultimate.txt"
    ).text  # this hosts file has over 700,000 entries 😵
    assert app.validateHostsFile(HOSTS)  # should be valid


def test_hagezi_ultimate_compressed_hosts():
    # another test just in case
    HOSTS = requests.get(
        "https://raw.githubusercontent.com/hagezi/dns-blocklists/main/hosts/ultimate-compressed.txt"
    ).text
    assert app.validateHostsFile(HOSTS)  # should also be valid
