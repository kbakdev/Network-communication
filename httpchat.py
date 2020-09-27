#!/usr/bin/python
# -*- coding: utf-8 -*-

# Note: because in Python 3 the socket.recv method returns bytes, not str,
# and most of the higher-level code works with strings
# (which are not fully compatible with bytes,
#  especially when it comes to comparisons or use as a key in a dictionary),
# in several places the program checks which version of the interpreter is
# dealing with and selects the appropriate version of the code to be executed.

import json
import os
import socket
import sys
from threading import Event, Lock, Thread

DEBUG = False # Changing to True displays additional messages.

# Implementation of website logic.
class SimpleChatWWW():
    def __init__(self, the_end):
        self.the_end = the_end
        self.files = "." # For example, the files may be in your working directory.

        self.file_cache = {}
        self.file_cache_lock = Lock()

        self.messages = []
        self.messages_offset = 0
        self.messages_lock = Lock()
        self.messages_limit = 1000 # Maximum number of stored messages.
        
        # Mapping web addresses to handlers.
        self.handlers = {
            ('GET', '/'):          self.__handle_GET_index,
            ('GET', 'index.html'): self.__handle_GET_index,
            ('GET', '/style.css'): self.__handle_GET_style,
            ('GET', '/main.js'):   self.__handle_GET_javascript,
            ('POST', '/chat'):     self.__handle_POST_chat,
            ('POST', '/messages'): self.__handle_POST_messages,
        }

    def handle_http_request(self, req):
        req_query = (req['method'], req['query'])
        if req_query not in self.handlers:
            return { 'status': (404, 'Not Found') }
        return self.handlers[req_query](req)

    def __handle_GET_index(self, req):
        return self.__send_file('httpchat_index.html')

    def __handle_GET_style(self, req):
        return self.__send_file('httpchat_style.css')

    def __handle_GET_javascript(self, req):
        return self.__send_file('httpchat_main.js')

    def __handle_POST_chat(self, req):
        # Read the needed fields from the received JSON object.
        # It is safe not to make any assumptions about the content and
        # type of data being transferred.
        try:
            obj = json.loads(req['data'])
        except ValueError:
            return { 'status': (400, 'Bad Request') }

        if type(obj) is not dict or 'text' not in obj:
            return { 'status': (400, 'Bad Request') }
        
        text = obj['text']
        if type(text) is not str and type(text) is not unicode:
            return { 'status': (400, 'Bad Request') }
        
        sender_ip = req['client_ip']

        # Add a message to the list.
        # If the list is longer than the limit,
        # remove one message in front and increase the offset.
        with self.messages_lock:
            if len(self.messages) > self.messages_limit:
                self.messages.pop(0)
                self.messages_offset += 1
            self.messages.append((sender_ip, text))

        sys.stdout.write("[  INFO ] <%s> %s\n" % (sender_ip, text))

        return { 'status': (200, 'OK') }

    def __handle_POST_messages(self, req):
        # Read the needed fields from the received JSON object.
        # It is safe not to make any assumptions about the content and type of data being transferred.
        try:
            obj = json.loads(req['data'])
        except ValueError:
            return { 'status': (400, 'Bad Request') }

        if type(obj) is not dict or 'last_message_id' not in obj:
            return { 'status': (400, 'Bad Request') }

        last_message_id = obj['last_message_id']

        if type(last_message_id) is not int:
            return { 'status': (400, 'Bad Request') }

        # Copy all messages, starting with last_message_id.
        with self.messages_lock:
            last_message_id -= self.messages_offset
            if last_message_id < 0:
                last_message_id = 0
            messages = self.messages[last_message_id:]
            new_last_message_id = self.messages_offset + len(self.messages)

        # Generate a response.
        data = json.dumps({
            "last_message_id": new_last_message_id,
            "messages": messages
        })

        return {
            'status': (200, 'OK'),
            'headers': [
                ('Content-Type', 'application/json;charset=utf-8'),
            ],
        'data': data
        }

    # Creating a response containing the contents of the file on the disk.
    # In practice, the method below additionally tries to cache files and read
    # them only if they have not already been loaded or if the file has changed
    # in the meantime.
    def __send_file(self, fname):
        # Determine the file type based on its extension.
        ext = os.path.splitext(fname)[1]
        mime_type = {
            '.html': 'text/html;charset=utf-8',
            '.js': 'application/javascript;charset=utf-8',
            '.css': 'text/css;charset=utf-8',
            }.get(ext.lower(), 'application/octet-stream')

        # Check when the file was last modified.
        try:
            mtime = os.stat(fname).st_mtime
        except:
            # Unfortunately, CPython on Windows throws an exception class that is not declared under GNU/Linux.
            # The easiest way is to catch all exceptions, although this is definitely an inelegant solution.

            # The file probably does not exist or cannot be accessed.
            return { 'status': (404, 'Not Found') }

        # Check if the file is in the cache.
        with self.file_cache_lock:
            if fname in self.file_cache and self.file_cache[fname][0] == mtime:
                return {
                    'status': (200, 'OK'),
                    'headers': [
                        ('Content-Type', mime_type),
                    ],
                'data': self.file_cache[fname][1]
                }

        # As a last resort, load the file.
        try:
            with open(fname, 'rb') as f:
                data = f.read()
                mtime = os.fstat(f.fileno()).st_mtime # Update the mime.
        except IOError as e:
            # Failed to read the file.
            if DEBUG:
                sys.stdout.write("[WARNING] File %s not found, but requested.\n" % fname)
            
            return { 'status': (404, 'Not Found') }

        # Add the contents of the file to the cache (unless another thread has done so in the meantime).
        with self.file_cache_lock:
            if fname not in self.file_cache or self.file_cache[fname][0] < mtime:
                self.file_cache[fname] = (mtime, data)

        # Send a reply with the contents of the file.
        return {
            'status': (200, 'OK'),
                'headers': [
                    ('Content-Type', mime_type),
                ],
            'data': data
            }

# A very simple implementation of a multi-threaded HTTP server.
class ClientThread(Thread):
    def __init__(self, website, sock, sock_addr):
        super(ClientThread, self).__init__()
        self.s = sock
        self.s_addr = sock_addr
        self.website = website

    def __recv_http_request(self):
        # Very simplified processing of an HTTP request with the main purpose of mining:
        # - methods
        # - desired path
        # - next parameters in the form of a dictionary
        # - additional data (in the case of POST)

        # Receive data until completion of header.
        data = recv_until(self.s, '\r\n\r\n')
        if not data:
            return None

        # Split the query into lines.
        lines = data.split('\r\n')

        # Analyze the query (first line).
        query_tokens = lines.pop(0).split(' ')
        if len(query_tokens) != 3:
            return None
        
        method, query, version = query_tokens

        # Load parameters.
        headers = {}
        for line in lines:
            tokens = line.split(':', 1)
            if len(tokens) != 2:
                continue

            # The capitalization of the header does not matter,
            # so it is a good idea to normalize it,
            # e.g. by converting all letters to lowercase.
            header_name = tokens[0].strip().lower()
            header_value = tokens[1].strip()
            headers[header_name] = header_value

            # For POST method, download additional data.
            # Note: the exemplary implementation in no way limits the number of transmitted data.
            if method == 'POST':
                try:
                    data_length = int(headers['content-length'])
                    data = recv_all(self.s, data_length)
                except KeyError as e:
                    # There is no Content-Length entry in the headers.
                    data = recv_remaining(self.s)
                except ValueError as e:
                    return None
            else:
                data = None

            # Put all relevant data in the dictionary and return it.
            request = {
                "method": method,
                "query": query,
                "headers": headers,
                "data": data,
                "client_ip": self.s_addr[0],
                "client_port": self.s_addr[1]
                }

            return request

        def __send_http_response(self, response):
            # Construct the HTTP response.
            lines = []
            lines.append('HTTP/1.1 %u %s' % response['status'])

            # Set the basic fields.
            lines.append('Server: example')
            if 'data' in response:
                lines.append('Content-Length: %u' % len(response['data']))
            else:
                lines.append('Content-Length: 0')
            
            # Rewrite the headlines.
            if 'headers' in response:
                for header in response['headers']:
                    lines.append('%s: %s' % header)
            
            lines.append('')

            # Rewrite the data.
            if 'data' in response:
                lines.append(response['data'])
            
            # Convert the response to bytes and send.
            if sys.version_info.major == 3:
                converted_lines = []
                for line in lines:
                    if type(line) is bytes:
                        converted_lines.append(line)
                    else:
                        converted_lines.append(bytes(line, 'utf-8'))
                    lines = converted_lines

                self.s.sendall(b'\r\n'.join(lines))
            
            def __handle_client(self):
                request = self.__recv_http_request()
                if not request:
                    if DEBUG:
                        sys.stdout.write("[WARNING] Client %s:%i doesn't make any sense. "
                                         "Disconnecting.\n" % self.s_addr)
                    return
                if DEBUG:
                    sys.stdout.write("[  INFO ] Client %s:%i requested %s\n" % (
                        self.s_addr[0], self.s_addr[1], request['query']))
                response = self.website.handle_http_request(request)
                self.__send_http_response(response)

            def run(self):
                self.s.settimeout(5) # Operations should not take longer than 5 seconds.

                try:
                    self.__handle_client()
                except socket.tiemout as e:
                    if DEBUG:
                        sys.stdout.write("[WARNING] Client %s:%i timed out. "
                                         "Disconnecting.\n" % self.s_addr)
                self.s.shutdown(socket.SHUT_RDWR)
                self.s.close()

        # Not a very quick but convenient function that receives data until a specific string (which is also returned) is encountered.
        def recv_until(sock, txt):
            txt = list(txt)
            if sys.version_info.major == 3:
                txt = [bytes(ch, 'ascii') for ch in txt]