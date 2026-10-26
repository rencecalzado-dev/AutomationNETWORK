import json
import re
from pathlib import Path
from getpass import getpass
from ipaddress import IPv4Network, IPv4Address

from netmiko import ConnectHandler


def main():
    config_path = Path(__file__).with_name("jsonderulo.json")
    config = json.loads(config_path.read_text(encoding="utf-8"))

    device = config["switch"].copy()
    dhcp = config["dhcp"]

    # Validate values before inserting them into CLI commands.
    network = IPv4Network(
        f'{dhcp["network"]}/{dhcp["subnet_mask"]}',
        strict=True,
    )
    gateway = IPv4Address(dhcp["default_gateway"])
    dns = IPv4Address(dhcp["dns_server"])
    first = IPv4Address(dhcp["excluded_start"])
    last = IPv4Address(dhcp["excluded_end"])
    pool = dhcp["pool_name"]
    ### lease = dhcp["lease_days"]

    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", pool):
        raise ValueError("Invalid DHCP pool name.")

    for address in (gateway, first, last):
        if address not in network or address in (
            network.network_address,
            network.broadcast_address,
        ):
            raise ValueError("Gateway and exclusions must be usable subnet IPs.")

    if not first <= gateway <= last:
        raise ValueError("Excluded range must contain the gateway.")

    ##if type(lease) is not int or not 0 <= lease <= 365:
        raise ValueError("Lease days must be an integer from 0 to 365.")

    device["password"] = getpass("Telnet VTY password: ")
    device["secret"] = getpass("Enable password: ")

    commands = [
        f"ip dhcp excluded-address {first} {last}",
        f"ip dhcp pool {pool}",
        f"network {network.network_address} {network.netmask}",
        f"default-router {gateway}",
        f"dns-server {dns}"
        ### f"lease {lease}",
    ]

    with ConnectHandler(**device) as switch:
        switch.enable()

        existing = switch.send_command(
            "show running-config | section dhcp"
        )
        if existing.lstrip().startswith("%"):
            raise RuntimeError("Could not read existing DHCP configuration.")

        print("\nExisting DHCP configuration:")
        print(existing or "(none)")

        if re.search(
            rf"(?m)^ip dhcp pool {re.escape(pool)}\s*$",
            existing,
        ):
            print("Pool already exists. No changes sent.")
            return

        print("\nProposed configuration:")
        print("\n".join(commands))

        if input("\nType APPLY to configure: ").strip() != "APPLY":
            print("Cancelled.")
            return

        print(switch.send_config_set(
            commands,
            error_pattern=r"(?m)^%.*",
        ))

        print("\nVerify:")
        print(switch.send_command("show running-config | section dhcp"))

        # Configuration is not automatically saved to startup-config.


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"Stopped: {error}")
        print("If changes started, inspect the switch configuration.")

