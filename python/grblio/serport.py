#!/usr/bin/env python3

import serial
import time
import port

class SerPort(port.Port):
  """connect to Grbl host via serial port"""
  def __init__(self, dev, baud=115200, timeout=1, eol="\r\n"):
    port.Port.__init__(self, eol)
    self.dev = dev
    self.baud = baud
    self.ser = serial.Serial()
    self.ser.port = dev
    self.ser.baud = baud
    self.ser.timeout = timeout
  
  def open(self):
    self.ser.open()
  
  def close(self):
    self.ser.close()
  
  def write(self, buf):
    """send a string as raw"""
    self.ser.write(buf.encode("utf-8"))
    
  def _read_ready(self, timeout):
    """can we read a line with read_line()?"""
    if self.ser.inWaiting() > 0:
      return True
    if timeout is not None:
      t = time.time()
      e = t + timeout
      while time.time() <= e:
        if self.ser.inWaiting() > 0:
          return True
        time.sleep(0.1)
    return False
  
  def _read(self):
    return self.ser.read(self.ser.inWaiting()).decode("utf-8")


if __name__ == '__main__':
  import sys
  import time
  if len(sys.argv) != 2:
    print("Usage:",sys.argv[0],"<serial_port>")
    sys.exit(1)
  dev = sys.argv[1]
  sp = SerPort(dev)
  t = port.PortTest(sp)
  t.run()
