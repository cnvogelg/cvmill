#!/usr/bin/env python3

import socket
import select
import port

class TcpPort(port.Port):
  """connect the Grbl host via a socat TCP pipe"""
  def __init__(self, hostname, hostport=5000, eol="\r\n"):
    port.Port.__init__(self, eol)
    self.hostname = hostname
    self.hostport = hostport
  
  def open(self):
    self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    self._socket.settimeout(1)
    self._socket.connect((self.hostname, self.hostport))

  def close(self):
    self._socket.shutdown(socket.SHUT_RDWR)
    self._socket.close()
    self._socket = None
    
  def write(self, buf):
    self._socket.sendall(buf.encode("utf-8"))
  
  def _read_ready(self, timeout):
    no = self._socket.fileno()
    res = select.select([no],[],[],timeout)
    ready = len(res[0]) > 0
    return ready
  
  def _read(self):
    return self._socket.recv(1024).decode("utf-8")


if __name__ == '__main__':
  import sys
  import time
  
  if len(sys.argv) != 2:
    print("Usage:",sys.argv[0],"<host>")
    sys.exit(1)
  host = sys.argv[1]
  tp = TcpPort(host)
  t = port.PortTest(tp)
  t.run()
