#!/usr/bin/python
# -*- coding: utf-8 -*-
import os
import socket
import sys
from datetime import timedelta
from struct import pack, unpack

def dns_query(query, domain, dnserver):
    # Create a socket that uses TCP (AF_INET, SOCK_STREAM).
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Connect to the indicated server on port 53.
    try:
        s.connect((dnserver, 53)) # DNS works on port 53.
    except socket.error as e:
        sys.stderr.write("error: failed to connect to server (%s)\n" % e.strerror)
    
    # Send an inquiry.
    dns_query_packet = dns_query_make_packet(query, domain)
    dns_tcp_send_packet(s, dns_query_packet)

    # Receive the answer.
    dns_response_packet = dns_tcp_recv_packet(s)
    dns_reply = dns_response_parse_packet(dns_response_packet)

    # Close the connection and socket.
    s.shutdown(socket.SHUT_RDWR)
    s.close()

    return dns_reply

