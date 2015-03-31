import time

class Port(object):
  """base class for all ports"""
  def __init__(self, timeout=1, eol="\r\n"):
    self.timeout = timeout
    self.eol = eol
    self.last_read = ""

  def open(self):
    raise

  def close(self):
    raise

  def write(self, buf):
    raise
  
  def canReadLine(self):
    raise

  def _readReady(self, timeout):
    raise

  def _read(self):
    raise

  def canReadLine(self, timeout=None):
    return len(self.last_read) > 0 or self._readReady(timeout)

  def readLine(self):
    """try to read a line until "\r\n" is received.
       block until something is read or return None on timeout"""
    # pre-fill buffer
    buf = self.last_read
    
    # already a line in it?
    pos = buf.find(self.eol)
    if pos < 0:
      # read into buf until eol is found
      start = time.time()
      while True:
        t = time.time()
        d = t - start
        if d >= self.timeout:
          break
        w = self.timeout - d
        if self._readReady(w):
          data = self._read()
          if data is None or len(data) == 0:
            break
          # contains line end?
          buf = buf + data
          pos = buf.find(self.eol)
          if pos >= 0:
            break
        else:
          time.sleep(0.1)
  
    # get first line in buf
    line = buf[0:pos]
    pos += len(self.eol)
    self.last_read = buf[pos:]
    return line

class PortTest(object):
  def __init__(self, port):
    self.port = port
  
  def run(self):
    sp = self.port
    print("opening")
    sp.open()
    print("sending reset")
    sp.write("\x18") # ctrl-x
    print("wait for line")
    sp.canReadLine()
    print("reading")
    while sp.canReadLine(1):
      l = sp.readLine()
      if l is not None:
        print("line:",len(l),l)
      else:
        print("no line")
    print("closing")
    sp.close()
    print("done")
