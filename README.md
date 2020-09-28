# TCP and DNS sockets
Commissioning and an exemplary execution are as follows:
```
$ python3 tcpdns.py
```

In order to check the correctness of the resulting data, it is worth comparing it with the result of the standard tools used to interact with DNS:
```
> nslookup kacper.bak.pl
> nslookup -type=MX bak.pl
```

# Listening TCP and HTTP sockets
A simple web chat based on an integrated, multi-threaded Python HTTP server using low-level sockets. Python, as well as other modern programming languages, has a set of libraries that enable the use of ready-made HTTP servers (e.g. the `BaseHTTPServer` class in Python 2.7 or `http.server` in Python 3). However, I decided to break it down into prime factors

You can test the server presented, for example using the irreplaceable console cURL tool.

<b>Terminal 1 (server):</b>
```
$ python3 httpchat.py
```

<b>Terminal 2 (curl):</b>
```
curl -v -d '{"text":"Hello World!"}' http://xxx.xxx.xx.xxx:8888/chat
```

Check your IP address with the `ifconfig` (Linux OS) or `ipconfig` (Windows OS) command.

Moving to the client-side part of the application, we will use a very simple architecture, which assumes the use of one static (in the sense of the server) page, on which changes (new messages) will be applied using a script in the background in JavaScript, using the popular jQuery libraries. The application will consist of three files.

As for the script that handles the user interface, it has two main functions:

- <b>Support for the text message field</b> - if the user presses the ENTER key with the message field selected, retrieve the message from the field, clear the text field, and then send a message request to the server in the background, indicating the resource `/chat` as the recipient. This method is popularly called AJAX (Asynchronus JavaScript and XML), although currently the XML format is used less frequently than the much simpler JSON (the method of serialization of the transferred data is of course optional and depends only on the programmer's choice).
- <b>Active polling of the server for new messages</b> - every 1000 ms send a background request with the ID of the latest known message to the server, indicating the resource `/messages` as the recipient. View all received messages in the message window.