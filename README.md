# TCP and DNS sockets
Commissioning and an exemplary execution are as follows:
```
$ python tcpdns.py
```

In order to check the correctness of the resulting data, it is worth comparing it with the result of the standard tools used to interact with DNS:
```
> nslookup kacper.bak.pl
> nslookup -type=MX bak.pl
```

# Listening TCP and HTTP sockets
A simple web chat based on an integrated, multi-threaded Python HTTP server using low-level sockets. Python, as well as other modern programming languages, has a set of libraries that enable the use of ready-made HTTP servers (e.g. the `BaseHTTPServer` class in Python 2.7 or `http.server` in Python 3).

You can test the server presented, for example using the irreplaceable console cURL tool.

<b>Terminal 1 (server):</b>
```
$ python httpchat.py
```

<b>Terminal 2 (curl):</b>
```
curl -v -d '{"text":"Hello World!"}` http://xxx.xxx.xx.xxx:8888/chat
```

Moving to the client-side part of the application, we will use a very simple architecture, which assumes the use of one static (in the sense of the server) page, on which changes (new messages) will be applied using a script in the background in JavaScript, using the popular jQuery libraries. The application will consist of three files.