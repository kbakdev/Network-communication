#!/usr/bin/python
# -*- coding: utf-8 -*-
import hashlib
import json
import os
import socket
import sys
import time
from struct import pack, unpack
from threading import Event, Lock, Thread

# Default port - it can be changed by specifying a different one in the script argument.
CHAT_PORT = 59999

PY3 = False
if sys.version_info.major == 3:
    PY3 = True

# Thread receiving messages.
class Receiver(Thread):
    def __init__(self, s, the_end, p2pchat):
        super(Receiver, self).__init__()
        self.s = s
        self.the_end = the_end
        self.p2pchat = p2pchat

    def run(self):
        while not self.the_end.is_set():
            try:
                # Receive a packet with the maximum possible UDP/IPv4 packet size.
                packet, addr = self.s.recvfrom(0xffff)
                if PY3:
                    packet = str(packet, 'utf-8')
                packet = json.loads(packet)
                t = packet["type"]
            except socket.timeout as e:
                continue
            except ValueError as e:
                # The case where the data is not properly formatted JSON.
                continue
            except KeyError as e:
                # Case where packet does not have "type" key defined.
                continue
            except TypeError as e:
                # The case where packet is not a dictionary.
                continue
            addr = "%s:%u" % addr
            self.p2pchat.handle_incoming(t, packet, addr)
        self.s.close()

class P2PChat():
    def __init__(self):
        self.nickname = ''
        self.s = None
        self.the_end = Event()
        self.nearby_users = set()
        self.known_messages = set()
        self.id_counter = 0
        self.unique_tag = os.urandom(16)
    
    def main(self):
        print("Enter your nickname: ", end="", flush=True)
        nickname = sys.stdin.readline()
        if not nickname:
            return
        self.nickname = nickname.strip()

        # Process starting IP of other users.
        port = CHAT_PORT
        if len(sys.argv) == 2:
            port = int(sys.argv[1])

        print("Creating UDP socket at port %u.\n"
              "To change the port, restart the app like this: upchat.py <port>\n" % port)

        # Create a UDP socket on the selected port and all interfaces.
        self.s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.s.settimeout(0.2)
        self.s.bind(("0.0.0.0", port))

        # Start a thread that receives data.
        th = Receiver(self.s, self.the_end, self)
        th.start()

        print("To start please add another user's address, e.g.:\n"
              "     /add 1.2.3.4\n"
              "     /add 1.2.3.4:59999\n"
              "     /add kacper.bak.pl:45454\n"
              "Or wait for a message form someone else.\n")
            
        # Go to the main loop.
        try:
            while not self.the_end.is_set():
                sys.stdout.write("? ")
                sys.stdout.flush()

                # Read line from user.
                ln = sys.stdin.realine()

                if not ln:
                    self.the_end.set()
                    continue

                ln = ln.strip()
                if not ln:
                    continue

                if ln[0] == '/':
                    # Order.
                    cmd = [1 for 1 in ln.split(' ' if len(1) > 0)]
                    self.handle_cmd(cmd[0], cmd[1:])
                else:
                    # Message.
                    self.send_message(ln)
        except KeyboardInterrupt as e:
                self.the_end.set()

        # The Receiver should close the socket when it exits.
        print("Bye!")

    def handle_incoming(self, t, packet, addr):
        # Packet with information about new neighboring node in P2P network.
        if t == "HELLO":
            print("# %s/%s connected" % (addr, packet["name"]))
            self.add_nearby_user(addr)
            return
            
