#!/usr/bin/env python3
import hashlib
import os
import random
import tempfile
import urllib.request

import tftpy
from scapy.all import BOOTP, DHCP, Ether, IP, UDP, get_if_hwaddr, sendp, sniff


IFACE = "eth0"
PXE_SERVER = "172.30.0.2"
CLIENT_IP = "172.30.0.3"
SUBNET_BROADCAST = "172.30.0.255"
HTTP_BASE = f"http://{PXE_SERVER}:8080"


def mac_bytes(mac):
    return bytes.fromhex(mac.replace(":", ""))


def option_value(options, name):
    for option in options:
        if isinstance(option, tuple) and option[0] == name:
            return option[1]
    return None


def discover(ipxe=False):
    mac = get_if_hwaddr(IFACE)
    xid = random.randint(1, 0xFFFFFFFF)
    options = [
        ("message-type", "discover"),
        ("client_id", b"\x01" + mac_bytes(mac)),
        ("param_req_list", [1, 3, 6, 15, 66, 67]),
    ]
    if ipxe:
        # iPXE uses encapsulated DHCP option 175 to advertise its features.
        options.append((175, b"\x13\x01\x01"))
    options.append("end")

    packet = (
        Ether(src=mac, dst="ff:ff:ff:ff:ff:ff")
        / IP(src=CLIENT_IP, dst=SUBNET_BROADCAST)
        / UDP(sport=68, dport=67)
        / BOOTP(
            chaddr=mac_bytes(mac) + b"\x00" * 10,
            xid=xid,
            flags=0,
        )
        / DHCP(options=options)
    )
    answers = sniff(
        iface=IFACE,
        timeout=8,
        lfilter=lambda candidate: (
            BOOTP in candidate
            and UDP in candidate
            and candidate[BOOTP].xid == xid
            and candidate[UDP].sport == 67
        ),
        started_callback=lambda: sendp(packet, iface=IFACE, verbose=False),
    )
    if not answers:
        raise AssertionError("DHCP OFFER was not received")
    answer = answers[0]

    message_type = option_value(answer[DHCP].options, "message-type")
    if message_type not in (2, "offer"):
        raise AssertionError(f"expected DHCP OFFER, got {message_type!r}")

    boot_file = bytes(answer[BOOTP].file).rstrip(b"\x00").decode()
    if not boot_file:
        option_boot_file = option_value(answer[DHCP].options, "boot-file-name")
        if isinstance(option_boot_file, bytes):
            boot_file = option_boot_file.decode().rstrip("\x00")
        elif option_boot_file:
            boot_file = str(option_boot_file)
    server_id = option_value(answer[DHCP].options, "server_id")
    return {
        "offered_ip": answer[BOOTP].yiaddr,
        "server_id": server_id,
        "next_server": answer[BOOTP].siaddr,
        "boot_file": boot_file,
        "options": answer[DHCP].options,
    }


def fetch_tftp_bootloader():
    with tempfile.TemporaryDirectory() as directory:
        destination = os.path.join(directory, "undionly.kpxe")
        client = tftpy.TftpClient(PXE_SERVER, 69)
        client.download("undionly.kpxe", destination, timeout=5, retries=3)
        with open(destination, "rb") as bootloader:
            content = bootloader.read()
    # undionly.kpxe is a binary PXE NBP.  Validate its minimum size and the
    # standard PXE structure markers rather than looking for a display string.
    if len(content) < 50_000 or b"!PXE" not in content or b"PXENV+" not in content:
        raise AssertionError("TFTP payload is not a valid PXE network boot program")
    return len(content), hashlib.sha256(content).hexdigest()


def http_get(path):
    with urllib.request.urlopen(f"{HTTP_BASE}/{path}", timeout=15) as response:
        return response.read()


def verify_http_stage():
    script = http_get("boot.ipxe").decode()
    required = ("#!ipxe", "vmlinuz-virt", "initramfs-virt", "modloop-virt", "boot")
    missing = [token for token in required if token not in script]
    if missing:
        raise AssertionError(f"boot.ipxe is missing: {', '.join(missing)}")

    sizes = {}
    for filename in ("vmlinuz-virt", "initramfs-virt", "modloop-virt"):
        payload = http_get(filename)
        if len(payload) < 1_000_000:
            raise AssertionError(f"{filename} is unexpectedly small")
        sizes[filename] = len(payload)
    return sizes


def main():
    legacy_offer = discover(ipxe=False)
    if legacy_offer["boot_file"] != "undionly.kpxe":
        raise AssertionError(
            f"legacy client got {legacy_offer['boot_file']!r}; "
            f"options={legacy_offer['options']!r}"
        )
    if legacy_offer["next_server"] != PXE_SERVER:
        raise AssertionError(f"unexpected TFTP server: {legacy_offer['next_server']}")
    print("[PASS] DHCP #1 (legacy PXE ROM)")
    print(
        f"  offer={legacy_offer['offered_ip']} next-server={legacy_offer['next_server']} "
        f"boot-file={legacy_offer['boot_file']}"
    )

    bootloader_size, bootloader_sha256 = fetch_tftp_bootloader()
    print(f"[PASS] TFTP: undionly.kpxe ({bootloader_size:,} bytes, PXE NBP markers found)")
    print(f"  sha256={bootloader_sha256}")

    ipxe_offer = discover(ipxe=True)
    expected_script = f"{HTTP_BASE}/boot.ipxe"
    if ipxe_offer["boot_file"] != expected_script:
        raise AssertionError(f"iPXE client got {ipxe_offer['boot_file']!r}")
    print("[PASS] DHCP #2 (chainloaded iPXE, option 175)")
    print(f"  boot-file={ipxe_offer['boot_file']}")

    sizes = verify_http_stage()
    print("[PASS] HTTP boot stage")
    for filename, size in sizes.items():
        print(f"  {filename:<16} {size:>12,} bytes")

    print("\nPXE chain verified: DHCP -> TFTP iPXE -> DHCP -> HTTP boot payloads")


if __name__ == "__main__":
    main()
