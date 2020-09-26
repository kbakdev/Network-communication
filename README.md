# Network-communication
Network communication

# TCP and DNS sockets
Commissioning and an exemplary execution are as follows:
``` $ python tcpdns.py ```

In order to check the correctness of the resulting data, it is worth comparing it with the result of the standard tools used to interact with DNS:
```
> nslookup kacper.bak.pl
> nslookup -type=MX bak.pl
```