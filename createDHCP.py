from getpass import getpass
from ipaddress import IPv4Network, IPv4Address

from netmiko import ConnectHandler


def main():
    device = {
        "device_type": "cisco_ios",
        "host": input("Router SSH IP: ").strip(),
        "username": input("Router username: ").strip(),
        "password": getpass("Router password: "),
        "secret": getpass("Enable secret (Enter if already privileged): "),
    }

    # Example: 192.168.102.0/24
    network = IPv4Network(input("DHCP subnet in CIDR: ").strip())
    gateway = IPv4Address(input("Router IP on that subnet: ").strip())
    first = IPv4Address(input("First excluded IP: ").strip())
    last = IPv4Address(input("Last excluded IP: ").strip())

    for address in (gateway, first, last):
        if address not in network or address in (
            network.network_address,
            network.broadcast_address,
        ):
            raise ValueError("Enter usable addresses inside the subnet.")

    if not first <= gateway <= last:
        raise ValueError("Excluded range must contain the gateway.")

    pool = "PYTHON-LAB"

    with ConnectHandler(**device) as router:
        router.enable()

        interfaces = router.send_command("show ip interface brief")
        existing = router.send_command(
            "show running-config | section dhcp"
        )

        print("\nCURRENT INTERFACES:")
        print(interfaces)
        print("\nEXISTING DHCP CONFIGURATION:")
        print(existing or "(none)")

        if f"ip dhcp pool {pool}" in existing:
            raise ValueError(f"Pool {pool} already exists. No changes sent.")

        commands = [
            f"ip dhcp excluded-address {first} {last}",
            f"ip dhcp pool {pool}",
            f"network {network.network_address} {network.netmask}",
            f"default-router {gateway}",
            "dns-server 8.8.8.8",
            "lease 1",
        ]

        print("\nPROPOSED CONFIGURATION:")
        print("\n".join(commands))
        print(
            "\nConfirm the subnet matches the lab interface, all static "
            "addresses are excluded, and no other DHCP server serves it."
        )

        if input("Type CREATE to apply: ").strip() != "CREATE":
            print("Cancelled.")
            return

        print(router.send_config_set(
            commands,
            error_pattern=r"(?m)^%.*",
        ))

        print("\nVERIFY DHCP CONFIGURATION:")
        print(router.send_command("show running-config | section dhcp"))
        print(router.send_command(f"show ip dhcp pool {pool}"))

        if input("Save ALL running configuration? Type SAVE: ").strip() == "SAVE":
            print(router.save_config())


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"Stopped: {error}")
        print("If changes started, inspect DHCP configuration in SecureCRT.")