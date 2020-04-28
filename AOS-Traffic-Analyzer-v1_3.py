#!/usr/bin/env python

import sys
import argparse
import time
import re
import os
import getpass

try:
    import paramiko
except ImportError as iepm:
    print(iepm)
    sys.exit("Please install paramiko!")
try:
    from prettytable import PrettyTable
except ImportError as iept:
    print(iept)
    sys.exit("Please install PrettyTable")

# === ArgParser === #

parser = argparse.ArgumentParser(description="Example Usage: AOS-Traffic-Analyzer 192.1.2.254 admin -p switch -r 10",
                                 epilog="Information regarding the interpretation of output: The value for bit/s shows \
                                         the last result from the system default 5 second measure intervall. \
                                         The values for broadcast and mulitcast are shown per second over the \
                                         last displayed samples.")
parser.add_argument("host", metavar="host", help="The IP address of the switch")
parser.add_argument("user", metavar="user", help="The user name for SSH access")
parser.add_argument("-p", metavar="password", help="The password for SSH access in cleartext. \
                                                    (If not entered, prompt will appear to type the password")
parser.add_argument("-r", "-repetitions", type=int, help="The number of measurements. (Default = 20)", default=20)
parser.add_argument("-i", "-intervall", type=int, help="The interval between measurements multiplied by 5. \
                                                        Try to increase if results seem to be incomplete. \
                                                        (Default = 1)", default=1)
parser.add_argument("-pc", "-pause_commands", type=float, help="The pause time between commands. \
                                                                Try to increase if results seem to be incomplete.\
                                                                (Default = 0.5)", default=0.5)
parser.add_argument("-t", "-trend", type=int, help="The amount of previous measurements to be displayed", default=1)
arguments = parser.parse_args()

arg_host = arguments.host
arg_user = arguments.user
# Take password from argparse if entered. If not, prompt user for password
if arguments.p:
    arg_password = arguments.p
else:
    arg_password = getpass.getpass(prompt="Password:", stream=None)
arg_repetitions = arguments.r
arg_intervall = arguments.i
arg_trend = arguments.t
arg_pause_between_commands = arguments.pc

# === Functions and classes === #


def clearscreen():  # Get OS System and perform clear-screen
    if os.name == 'nt':
        _ = os.system("cls")
    else:
        _ = os.system("clear")


class SshAos:
    def __init__(self, host, user, password):
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())  # no verification of host key!
        self.ssh.connect(hostname=host, port=22, username=user, password=password)
        self.channel = self.ssh.invoke_shell()

    def send_command(self, command):
        self.channel.send(command+"\n")

    def receive_output(self, pause):
        time.sleep(pause)
        output = self.channel.recv(65536)
        return(output.decode("utf-8"))

    def disconnect(self):
        self.channel.send("exit\n")
        self.channel.close()
        self.ssh.close()

# === Main Programm === #


def main():

    # ===========================================================
    # Free script written by Benjamin Domroese in 2019, use at your own risk
    # and test first in non-productive enviroment!
    # This paramiko settings do not validate host keys!
    # =============================================================

    # Declaration of variables
    output_table = PrettyTable(["Port", "InMbit/s", "OutMbit/s", "InBCast Pkt/s",
                                "OutBCast Pkt/s", "InMCast Pkts/s", "OutMCast Pkt/s"], hrules=1, title="test")
    output_table.align = "r"

    # Connect to switch and get information about active interfaces
    switch1 = SshAos(arg_host, arg_user, arg_password)
    switch1.send_command("show interfaces status")
    output = switch1.receive_output(arg_intervall)

    # Bugfix in v1.3, get the session prompt to filter it from output values
    switch1.send_command("show session config")
    output_sessionprompt = switch1.receive_output(arg_intervall)
    rx_sessionprompt = re.compile(r"Prompt\s+\=\s+(.+)\,")
    session_prompt = str(re.search(rx_sessionprompt, output_sessionprompt).group(1))

    # Get all active ports in a list (different RegEx for AOS6/8)
    rx6 = re.compile(r".*(\d{1}/\d{1,2}/?\d{0,2})\s+Enable\s+\d+\s+\S+")
    rx8 = re.compile(r".*(\d{1}/\d{1,2}/\d{0,2})\s+en\s+\S{1,5}\s+\d+")
    all_active_ports = re.findall(rx6, output)
    if len(all_active_ports) == 0:  # Use AOS8 Regex, if no ports found for AOS6
        all_active_ports = re.findall(rx8, output)

    # Create a list for all active ports with initial values of 0, to be able to compare values.
    list_port_values = [[{"Port": all_active_ports[port], "InBits":"0", "OutBits":"0", "InBCast":"0", "OutBCast":"0",
                          "InMCast":"0", "OutMCast":"0"}] for port in range(len(all_active_ports))]

    # Help Variable to get a packet per second value for broad and multicast
    divisor_for_packets_per_second = (arg_intervall * 5 + (arg_pause_between_commands * (len(all_active_ports))))

    # Iterate through all Ports every 5 seconds
    for round in range(1, arg_repetitions):
        for port in range(len(all_active_ports)):
            switch1.send_command("show interfaces " + all_active_ports[port] + " counters")
            time.sleep(arg_pause_between_commands)

        output = switch1.receive_output(arg_intervall*5)
        output_clean = "".join(output.split())  # Make it easier for RegEx, to match the values

        #Bugfix in v1.3, if session promt contains numbers - it had been added to the outbits. 
        #Remove session promtpt from output_clean
        output_clean = re.sub(session_prompt,"",output_clean)

        # Create RegEx for every active Ports in list
        for port in range(len(all_active_ports)):
            rxp1_in_bits = r"{}.*?(InBits/s\=)(\d+)".format(all_active_ports[port])
            rxp1_out_bits = r"{}.*?(OutBits/s\=)(\d+)".format(all_active_ports[port])
            rxp1_in_mcast_pkts = r"{}.*?(InMcastPkts\=)(\d+)".format(all_active_ports[port])
            rxp1_out_mcast_pkts = r"{}.*?(OutMcastPkts\=)(\d+)".format(all_active_ports[port])
            rxp1_in_bcast_pkts = r"{}.*?(InBcastPkts\=)(\d+)".format(all_active_ports[port])
            rxp1_out_bcast_pkts = r"{}.*?(OutBcastPkts\=)(\d+)".format(all_active_ports[port])

            if re.search(rxp1_in_bits, output_clean):
                int_bit_s = int(re.search(rxp1_in_bits, output_clean).group(2))
                if int_bit_s > 0:
                    int_bit_s = int_bit_s / 1024 / 1024  # convert to Megabit/s and check Device/0 Error
                else:
                    int_bit_s = 0.00
                value_in_bits = "{:0.2f}".format(int_bit_s)  # Format settings to two digits after commata

            if re.search(rxp1_out_bits, output_clean):
                int_bit_s = int(re.search(rxp1_out_bits, output_clean).group(2))
                if int_bit_s > 0:
                    int_bit_s = int_bit_s / 1024 / 1024  # convert to Megabits/s and check Device/0 Error
                else:
                    int_bit_s = 0.00
                value_out_bits = "{:0.2f}".format(int_bit_s)

            if re.search(rxp1_in_bcast_pkts, output_clean):
                int_pkts_s = int(re.search(rxp1_in_bcast_pkts, output_clean).group(2))
                value_in_bcast_pkts = int_pkts_s

            if re.search(rxp1_out_bcast_pkts, output_clean):
                int_pkts_s = int(re.search(rxp1_out_bcast_pkts, output_clean).group(2))
                value_out_bcast_pkts = int_pkts_s

            if re.search(rxp1_in_mcast_pkts, output_clean):
                int_pkts_s = int(re.search(rxp1_in_mcast_pkts, output_clean).group(2))
                value_in_mcast_pkts = int_pkts_s

            if re.search(rxp1_out_mcast_pkts, output_clean):
                int_pkts_s = int(re.search(rxp1_out_mcast_pkts, output_clean).group(2))
                value_out_mcast_pkts = int_pkts_s

            # Create Dictionary with the found values
            list_port_values[port].append({"Port": all_active_ports[port],
                                           "InBits": value_in_bits,
                                           "OutBits": value_out_bits,
                                           "InBCast": value_in_bcast_pkts,
                                           "OutBCast": value_out_bcast_pkts,
                                           "InMCast": value_in_mcast_pkts,
                                           "OutMCast": value_out_mcast_pkts})

            # Create Output Table with values to be shown
            # Variables to be cleaned, before calcualted for beeing displayed
            value_cell_1 = ""
            value_cell_2 = ""
            value_cell_3 = ""
            tmp_float_c3 = ""
            value_cell_4 = ""
            tmp_float_c4 = ""
            value_cell_5 = ""
            tmp_float_c5 = ""
            value_cell_6 = ""
            tmp_float_c6 = ""

            # Create trending view, for the number of -t by argparse
            # Provided additional check against Devide/0 exception.
            for i in range(round):
                if i < arg_trend:

                    value_cell_1 += list_port_values[port][round - i]["InBits"]
                    value_cell_2 += list_port_values[port][round - i]["OutBits"]

                    tmp_float_c3 = "{:0.2f}".format((list_port_values[port][round-i]["InBCast"] - int(
                        list_port_values[port][round - (i+1)]["InBCast"])) / divisor_for_packets_per_second) \
                        if (list_port_values[port][round-i]["InBCast"] - int(
                            list_port_values[port][round - (i+1)]["InBCast"])) > 0 else "0.00"
                    value_cell_3 += str(tmp_float_c3)

                    tmp_float_c4 = "{:0.2f}".format((list_port_values[port][round - i]["OutBCast"] - int(
                        list_port_values[port][round - (i + 1)]["OutBCast"])) / divisor_for_packets_per_second) \
                        if (list_port_values[port][round - i]["OutBCast"] - int(
                            list_port_values[port][round - (i + 1)]["OutBCast"])) > 0 else "0.00"
                    value_cell_4 += str(tmp_float_c4)

                    tmp_float_c5 = "{:0.2f}".format((list_port_values[port][round - i]["InMCast"] - int(
                        list_port_values[port][round - (i + 1)]["InMCast"])) / divisor_for_packets_per_second) \
                        if (list_port_values[port][round - i]["InMCast"] - int(
                            list_port_values[port][round - (i + 1)]["InMCast"])) > 0 else "0.00"
                    value_cell_5 += str(tmp_float_c5)

                    tmp_float_c6 = "{:0.2f}".format((list_port_values[port][round - i]["OutMCast"] - int(
                        list_port_values[port][round - (i + 1)]["OutMCast"])) / divisor_for_packets_per_second) \
                        if (list_port_values[port][round - i]["OutMCast"] - int(
                            list_port_values[port][round - (i + 1)]["OutMCast"])) > 0 else "0.00"
                    value_cell_6 += str(tmp_float_c6)
                else:
                    break

                if i + 1 < arg_trend:  # Add carriage return only if it is not the last line in a cell
                    value_cell_1 += "\n"
                    value_cell_2 += "\n"
                    value_cell_3 += "\n"
                    value_cell_4 += "\n"
                    value_cell_5 += "\n"
                    value_cell_6 += "\n"

            output_table.add_row([all_active_ports[port], value_cell_1, value_cell_2, value_cell_3, value_cell_4,
                                  value_cell_5, value_cell_6])

        clearscreen()
        print("       ======================================================\n")
        print("                    Traffic Stats for Switch {} \n".format(arg_host))
        print("       ======================================================\n")
        print(output_table)
        output_table.clear_rows()


if __name__ == "__main__":
    main()



