import time
import uuid
import logging
import paramiko
import interactive

from config import settings


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
        self.channel.close()
        self.transport.close()

    def interactive(self):
        interactive.interactive_shell(self.channel)

    def enter_server(self, server_id=1):
        """select server via the interactive GateShell
        server_id: range from 1 to 50
        """
        assert 1 <= server_id <= 50

        logging.info(f"selecting server-{server_id:02d}")
        messages = [
            ":",  # enter search mode
            f"{server_id}",  # enter server_id
            "\n",  # press enter to search
            "\n",  # connect the target server
        ]
        for msg in messages:
            time.sleep(0.5)
            self.channel.send(msg)

        logging.info(f"initializing shell on server-{server_id:02d}")
        initial_commands = [
            # disable tty echo
            "stty -ctlecho -echo -echoctl -echoe -echok -echoke -echonl -echoprt",
            # unset ls color
            "unset LS_COLORS",
        ]

        for initial_command in initial_commands:
            logging.info(initial_command)
            time.sleep(0.5)
            self.channel.send(f"{initial_command}\n")

    def exit_server(self):
        self.channel.send("exit\n")

    def shell_exec(self, command):
        # execute the command
        logging.info(f"executing {command}")
        nonce1 = str(uuid.uuid4())
        nonce2 = str(uuid.uuid4())
        self.channel.send(f"echo {nonce1} && {command} && echo {nonce2}\n")
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


def main():
    logging.basicConfig()
    logging.getLogger("paramiko").setLevel(logging.INFO)
    client = DBAppSecurityUSM()
    client.auth()

    command = "hostname && head -n 1 /etc/passwd"
    for i in range(4):
        server_id = i + 1
        client.enter_server(server_id=server_id)
        print(client.shell_exec(command).decode("utf-8"))
        client.exit_server()

    client.close()


if __name__ == "__main__":
    main()
