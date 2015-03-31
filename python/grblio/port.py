import time

class Port(object):
  """base class for all ports"""
  def __init__(self, eol="\r\n"):
    self.eol = eol
    self.last_read = ""

  def open(self):
    raise

  def close(self):
    raise

  def write(self, buf):
    raise
  
  def _read_ready(self, timeout):
    raise

  def _read(self):
    raise

  def can_read_line(self, timeout=None):
    return len(self.last_read) > 0 or self._read_ready(timeout)

  def read_line(self, timeout=None):
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
        if timeout is not None:
          if d >= timeout:
            break
          w = timeout - d
        else:
          w = 0.1
        if self._read_ready(w):
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
    pos = buf.find(self.eol)
    if pos >= 0:
      line = buf[0:pos]
      pos += len(self.eol)
      self.last_read = buf[pos:]
      return line
    else:
      self.last_read = buf
      return None


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
    sp.can_read_line()
    print("reading")
    while sp.can_read_line(1):
      l = sp.read_line()
      if l is not None:
        print("line:",len(l),l)
      else:
        print("no line")
    print("closing")
    sp.close()
    print("done")
