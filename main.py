import verboselogs
import uuid
import timeout_decorator
import time
import paramiko
import logging
import coloredlogs
import os

import interactive
from config import settings


logger = verboselogs.VerboseLogger(os.path.basename(__file__))
paramiko_logger = logging.getLogger("paramiko")
coloredlogs.install(level="INFO", logger=logger)
coloredlogs.install(level="INFO", logger=paramiko_logger)


class DBAppSecurityUSM:
    def __init__(self):
        self.transport = paramiko.Transport(settings.DBAPP_SECURITY_USM_ENDPOINT)

    @staticmethod
    def get_otp():
        import pyotp

        otp = pyotp.TOTP(settings.DBAPP_SECURITY_USM_OTP_SECRET).now()
        return str(otp)

    @staticmethod
    def dbapp_security_usm_auth_handler(title, instructions, prompt_list):
        return (DBAppSecurityUSM.get_otp(),)

    def auth(self):
        self.transport.connect()
        self.transport.auth_password(
            username=settings.DBAPP_SECURITY_USM_USERNAME,
            password=settings.DBAPP_SECURITY_USM_PASSWORD,
        )
        self.transport.auth_interactive(
            username=settings.DBAPP_SECURITY_USM_USERNAME,
            handler=DBAppSecurityUSM.dbapp_security_usm_auth_handler,
        )
        self.channel = self.transport.open_session()
        self.channel.get_pty()
        time.sleep(1)
        self.channel.invoke_shell()
        time.sleep(1)

    def close(self):
        logger.warning(f"closing the connection to {settings.DBAPP_SECURITY_USM_ENDPOINT}")
        self.channel.close()
        self.transport.close()

    def interactive(self):
        interactive.interactive_shell(self.channel)

    def enter_server(self, server_id=1):
        """select server via the interactive GateShell
        server_id: range from 1 to 50
        """
        assert 1 <= server_id <= 50

        logger.debug(f"selecting the {server_id}th server")
        messages = [
            "/",  # enter search mode
            f"DNS_test{server_id:02d}",  # enter server_id
            "\n",  # press enter to search
            "\n",  # connect the target server
        ]
        for msg in messages:
            time.sleep(0.5)
            self.channel.send(msg)

        logger.debug(f"initializing shell on the {server_id}th server")
        initial_commands = [
            # disable tty echo
            "stty -ctlecho -echo -echoctl -echoe -echok -echoke -echonl -echoprt",
            # unset ls color
            "unset LS_COLORS",
        ]

        for initial_command in initial_commands:
            logger.debug(initial_command)
            time.sleep(0.5)
            self.channel.send(f"{initial_command}\n")

    def exit_server(self):
        self.channel.send("exit\n")

    def shell_exec(self, command):
        # execute the command
        logger.debug(f"executing {command}")
        nonce1 = str(uuid.uuid4())
        nonce2 = str(uuid.uuid4())
        self.channel.send(f"echo {nonce1} && {command} ; echo {nonce2}\n")
        self.__recv_until(self.channel, nonce1)
        response = self.__recv_until(self.channel, nonce2)
        return response.rstrip(nonce2.encode("utf-8")).strip()

    def __recv_until(self, channel, pattern):
        response = b""
        while not response.endswith(pattern.encode("utf-8")):
            ch = channel.recv(1)
            if not ch:
                break
            response += ch
        return response


@timeout_decorator.timeout(60)
def enter_shell_exec_exit(client, server_id, command):
    logger.warning(f"[node-{server_id:02d}] $ {command}")
    client.enter_server(server_id=server_id)
    result = client.shell_exec(command).decode("utf-8")
    logger.success(result)
    client.exit_server()
    return result


def derive_new_client():
    logger.info(f"derive a new connection to {settings.DBAPP_SECURITY_USM_ENDPOINT}")
    client = DBAppSecurityUSM()
    client.auth()
    return client


def batch(commands):
    client = derive_new_client()
    results = {}
    for i in range(50):
        server_id = i + 1
        if server_id not in results.keys():
            results[server_id] = []
        for command in commands:
            try:
                result = enter_shell_exec_exit(client, server_id, command)
            except Exception as e:
                logger.error(f"the {server_id}th server does not respond, {repr(e)}")
                client.close()
                client = derive_new_client()
                result = None
        results[server_id].append((command, result))
    client.close()
    return results


def convert_commands_to_shell_script(commands):
    filepath = "/tmp/setup-docker.sh"
    echo_commands = [f"echo '#!/bin/bash' > {filepath}"] + [f"echo {repr(i)} >> {filepath}" for i in commands]
    batch([" && ".join(echo_commands)])
    return filepath


def setup():
    """
    [1] https://docs.docker.com/engine/install/centos/
    """
    commands = [
        "docker --version",
        "sudo yum remove docker docker-client docker-client-latest docker-common docker-latest docker-latest-logrotate docker-logrotate docker-engine",
        "sudo yum install -y yum-utils",
        "sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo",
        "sudo yum install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin",
        "sudo systemctl start docker",
        "sudo systemctl enable docker",
        "sudo docker run hello-world",
    ]
    return convert_commands_to_shell_script(commands)


def check_docker_version():
    batch(["docker --version"])


def check_docker_compose_version():
    batch(["docker compose version"])


def main():
    # # step 1: check docker and compose version
    check_docker_version()
    check_docker_compose_version()
    # step 2: upload shell script
    filepath = setup()
    # step 3: run shell script
    batch([f"cat {filepath} && /bin/bash -c 'nohup /bin/bash -x {filepath} &' && bash -c 'ps aux | grep {filepath}'"])
    # step 4: check running status
    batch(["tail -n 10 nohup.out"])


if __name__ == "__main__":
    main()
