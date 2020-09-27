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
        # 