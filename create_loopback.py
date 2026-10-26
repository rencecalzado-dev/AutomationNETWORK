import re
from getpass import getpass

from netmiko import ConnectHandler


LOOPBACK = "Loopback100"
LOOPBACK_IP = "1.1.1.1"
MASK = "255.255.255.255"


def main():
    router_ip = input("Router SSH IP: ").strip()
    username = input("Router username: ").strip()
    password = getpass("Router password: ")
    ###secret = getpass("Enable secret (Enter if already privileged): ")

    device = {
        "device_type": "cisco_ios",
        "host": router_ip,
        "username": username,
        "password": password,
        ### "secret": secret,
        ### "conn_timeout": 15,
    }

    with ConnectHandler(**device) as router:
        router.enable()
        print(f"\nConnected to {router.find_prompt()}")

        # Read existing configuration before making any changes.
        interfaces = router.send_command("show ip interface brief")
        addresses = router.send_command(
            "show running-config | include ip address"
        )

        if "%" in interfaces or "%" in addresses:
            raise RuntimeError("Precheck command failed. No changes sent.")

        if re.search(rf"(?mi)^{LOOPBACK}\s", interfaces):
            print(f"{LOOPBACK} already exists. No changes sent.")
            return

        if re.search(
            rf"(?m)^\s*ip address {re.escape(LOOPBACK_IP)}\s",
            addresses,
        ):
            print(f"{LOOPBACK_IP} is already configured. No changes sent.")
            return

        commands = [
            f"interface {LOOPBACK}",
            "description Created by Python Netmiko lab",
            f"ip address {LOOPBACK_IP} {MASK}",
            "no shutdown",
        ]

        print("\nProposed configuration:")
        print("\n".join(commands))

        answer = input("\nType CREATE to apply: ").strip()
        if answer != "CREATE":
            print("Cancelled. No changes sent.")
            return

        output = router.send_config_set(
            commands,
            error_pattern=r"(?m)^%.*",
        )
        print(output)

        config = router.send_command(
            f"show running-config interface {LOOPBACK}"
        )
        status = router.send_command("show ip interface brief")

        print("\nVerification:")
        print(config)
        print(status)

        expected_ip = f"ip address {LOOPBACK_IP} {MASK}"
        is_up = re.search(
            rf"(?mi)^{LOOPBACK}\s+{re.escape(LOOPBACK_IP)}"
            rf"\s+YES\s+\S+\s+up\s+up\s*$",
            status,
        )

        if expected_ip not in config or not is_up:
            raise RuntimeError(
                "Verification failed. Inspect the running configuration "
                "in SecureCRT. Changes were not saved to startup-config."
            )

        print("\nSuccess: Loopback100 is configured and up/up.")

        if input("Save ALL running configuration? Type SAVE: ").strip() == "SAVE":
            print(router.save_config())
        else:
            print("Loopback remains in running-config only.")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"\nStopped: {error}")
        print(
            "If configuration had started, inspect Loopback100 "
            "in SecureCRT before retrying."
        )