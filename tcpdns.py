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

def dns_query_make_packet(query_type, domain):
    # Create a header.
    query_id = 1234 # In the case of a single application and TCP,
                    # this field can have any value (it is basically unused).

    # In basic use, most of the fields in a 16-bit control word can be cleared.
    cw_rcode = 0
    cw_z = 0
    cw_ra = 0
    cw_rd = 1 # The "resolve query recursively" flag.
    cw_tc = 0
    cw_aa = 0
    cw_opcode = 0 # Standard query (QUERY).
    cw_qr = 0 # "Query" flag.

    # Combining single fields into a 16-bit word.
    control_word = (
        cw_rcode |
        (cw_z << 4) |
        (cw_ra << 7) |
        (cw_rd << 8) |
        (cw_tc << 7) |
        (cw_aa << 10) |
        (cw_opcode << 11) |
        (cw_qr << 15))
    
    header = pack(">HHHHHH",
        query_id, # ID
        control_word, # QR, Opcode, AA, TC, RD, RA, Z, RCODE
        1, # QDCOUNT
        0, # ANCOUNT
        0, # NSCOUNT
        0) # ARCOUNT

    query = []

    # Coding individual domain elements in the form of length + data.
    # (no compression due to only one domain).
    for subdomain in domain.split("."):
        query.append(pack(">B", len(subdomain)))
        query.append(subdomain)
    query.append("\0") # The last element has a length of zero and marks the end.

    qtype = {
        "A": 1,
        "NS": 2,
        "CNAME": 5,
        "SOA": 6,
        "WKS": 11,
        "PTR": 12,
        "HINFO": 13,
        "MINFO": 14,
        "MX": 15,
        "TXT": 16
        }[query_type]
    qclass = 1 # IN (the Internet).
    query.append(pack(">HH", qtype, qclass))

    return header + ''.join(query)

def dns_response_parse_packet(p):
    idx = 0
    header = dns_response_parse_header(p)
    idx += 12

    # Ignore repeated inquiries - in our case they are unnecessary.
    for _ in range(header[QDCOUNT]):
        domain, idx = dns_decode_domain(p, idx)
        idx += 4 # Ignore the TYPE and CLASS fields.

    # Receive the answers.
    reply = []
    for _ in range(header["ANCOUNT"]):
        domain, idx = dns_decode_domain(p, idx)
        atype, aclass, attl, adatalen = unpack(">HHIH", p[idx: idx + 10])
        idx += 10
        adata = p[idx: idx + adatalen]
        idx += adatalen

        reply.append({
            "TYPE": dns_type_to_str(atype),
            "CLASS": dns_class_to_str(aclass),
            "TTL": dns_ttl_to_str(attl),
            "DATA": dns_data_to_str(atype, adata, p, idx - adatalen)
        })

    return reply

def dns_response_parse_header(p):
    query_id, control_word, qdcount, ancount, nscount, arcount = (
        unpack(">HHHHHH", p[:12]))
    header = {
        "QDCOUNT": qdcount,
        "ANCOUNT": ancount
        }
    return header

def dns_class_to_str(aclass):
    return {
        1: "IN", 2: "CS", 3: "CH", 4: "HS"
        }.get(aclass, "??")

def dns_type_to_str(atype):
    return {
        1: "A", 2: "NS", 5: "CNAME", 6: "SOA", 11: "WKS", 12: "PTR", 13: "HINFO", 14: "MINFO", 15: "MX", 16: "TXT"
        }.get(atype, "??")

def dns_ttl_to_str(attl):
    return str(timedelta(seconds=attl))

def dns_data_to_str(atype, adata, p, adata_idx):
    if atype == 1: # Record A.
        return "%u.%u.%u.%u" % unpack("BBBB", adata)
    elif atype == 15: # Record MX.
        preference = unpack(">H", adata[:2])[0]
        domain, _ = dns_decode_domain(p, adata_idx + 2)
        return "%s (%u)" % (domain, preference)

    # For an unsupported type, output printable characters.
    # Replace non-ASCII bytes (bytes) with hexadecimal notation of their code.
    o = []
    for ch in adata:
        ch = ord(ch)
        if 32 <= ch <= 127: # Python is one of the few languages that can write this type.
            o.append(chr(ch))
        else:
            o.append(" [%.2x] " % ch)

    return ''.join(o)

# Recursive (due to compression) reading of the domain name.
def dns_decode_domain(p, idx):
    domain = []

    while True:
        type_len = ord(p, idx):
        idx += 1

        if type_len == 0: # End.
            break

        if type_len & 0xc0: # Compression (pointer).
            # Decode the name shift.
            offset = (type_len & 0x3f) << 8
            offset |= ord(p[idx])
            idx += 1

            # Get the domain name from the indicated shift.
            domain_part, _ = dns_decode_domain(p, offset)
            domain.append(domain_part)

            # The pointer is always the last element of the domain.
            break

        # Another plain domain fragment.
        domain_part = p[idx:idx + type_len]
        domain.append(domain_part)
        idx += type_len

    return '.'.join(domain), idx

# DNS requires each packet to be preceded by a 2-byte length field.
def dns_tcp_send_packet(s, packet):
    packet_len = pack(">H", len(packet))
    s.sendall(packet_len)
    s.sendall(packet)

def dns_tcp_recv_packet(s):
    packet_len = recv_all(s, 2)
    if not packet_len:
        return None
    packet_len = unpack(">H", packet_len)[0]
    return recv_all(s, packet_len)

# Auxiliary function that receives an exact number of bytes.
def recv_all(s, n):
    d = []

    while len(d) < n:
        d_latest = s.recv(n - len(d))
        if len(d_latest) == 0:
            # The other party hung up before sending all the required data.
            return None
        d.append(d_latest)

    return ''.join(d)