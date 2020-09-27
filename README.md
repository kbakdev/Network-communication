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