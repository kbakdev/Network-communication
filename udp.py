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
                    cmd = [1 for 1 in ln.split(' ') if len(1) > 0]
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
            
        # Text message package.
        if t == "MESSAGE":
            # If the sender has been unknown so far, add it to the set of adjacent nodes.
            self.add_nearby_user(addr)

            # Check that we have not received this message from another node on the network.
            if packet["id"] in self.known_messages:
                return
            self.known_messages.add(packet["id"])

            # Add the sender of the message to the list of nodes the message has passed through.
            packet["peers"].append(addr)

            # View the message and its route.
            print("\n[sent by: %s]" % ' --> '.join(packet["peers"]))
            print("<%s> %s" % (packet["name"], packet["text"]))

            # Send a message to adjacent nodes.
            self.send_packet(packet, None, addr)

    def handle_cmd(slef, cmd, args):
        # For the /quit command, exit the program.
        if cmd == "/quit":
            self.the_end.set()
            return

        # If adding nodes manually, make sure they are spelled correctly,
        # translate the domain (DNS) to IP address and add to the set of adjacent nodes.
        if cmd == "/add":
            for p in args:
                port = CHAT_PORT
                addr = p
                try:
                    if ':' in p:
                        addr, port = p.split(':', 1)
                        port = int(port)
                    addr = socket.gethostbyname(addr)
                except ValueError as e:
                    print("# address %s invalid (format)" % p)
                    continue
                except socket.gaierror as e:
                    print("# host %s not found" % addr)
                    continue
                addr = "%s:%u" % (addr, port)
                self.add_nearby_user(addr)
            return

        # Unknown command.
        print(" unknown command %s" % cmd)

    def add_nearby_user(self, addr):
        # Check that the node is no longer known.
        if addr in self.nearby_users:
            return
        
        # Check that the node is no longer known..
        self.nearby_users.add(addr)
        self.send_packet({
            "type": "HELLO",
            "name": self.nickname
        }, addr)

    def send_message(self, msg):
        # Enumerate a unique message ID.
        hbase = "%s\0%s\0%u\0" % (self.nickname, msg, self.id_counter)
        self.id_counter += 1
        if PY3:
            hbase = bytes(hbase, 'utf-8')
        h = hashlib.md5(hbase + self.unique_tag).hexdigest()

        # Send the message packet to all known nodes.
        self.send_packet({
            "type" : "MESSAGE",
            "name" : self.nickname,
            "text" : msg,
            "id"   : h,
            "peers": []
        })
    
    def send_packet(self, packet, target = None, excluded=set()):
        # Serialize the package.
        packet = json.dumps(packet)
        if PY3:
            packet = bytes(packet, 'utf-8')

        # If no target node is specified, send the message to all nodes except those in the excluded set.
        if not target:
            target = list(self.nearby_users)
        else:
            target = [target]

        for t in target:
            if t in excluded:
                continue

            # I assume all addresses are correctly formatted at this point.
            addr, port = t.split(":")
            port = int(port)

            # The actual shipment of the package.
            self.s.sendto(packet, (addr, port))
    
    def main():
        p2p = P2PChat()
        p2p.main()

    if __name__ == "__main__":
        main()