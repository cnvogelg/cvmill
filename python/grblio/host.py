# grblhost.py
# 
# a host interface for the grbl firmware

import re
import time

# event constants
ID_OK = 0
ID_ERROR = 1
ID_ALARM = 2
ID_INFO = 3
ID_STATE = 4

event_names = (
  "ok",
  "error",
  "alarm",
  "info",
  "state"
)

# state
STATE_IDLE = 0
STATE_QUEUED = 1
STATE_CYCLE = 2
STATE_HOLD = 3
STATE_HOMING = 4
STATE_ALARAM = 5
STATE_CHECK_MODE = 6

state_names = (
  "Idle",
  "Queued",
  "Cycle",
  "Hold",
  "Homing",
  "Alarm",
  "Check_Mode"
)

# ----- Errors -----
class GrblBaseError(Exception):
  pass

class GrblHostError(GrblBaseError):
  def __init__(self, msg):
    self.msg = msg

  def __str__(self):
    return "GrblHostError: " + self.msg

class GrblEventError(GrblBaseError):
  def __init__(self, event):
    self.event = event

  def __str__(self):
    return "GrblEventError: " + self.event

class GrblStateError(GrblBaseError):
  def __init__(self, state):
    self.state = state

  def __str__(self):
    return "GrblStateError: " + self.state


# ----- Helper Classes -----
class GrblEvent:
  def __init__(self, id, data=None):
    self.id = id
    self.data = data

  def __str__(self):
    if self.data != None:
      return "{%s,%s}" % (event_names[self.id], self.data)
    else:
      return "{%s}" % event_names[self.id]


class GrblState:
  def __init__(self, id, mpos, wpos):
    self.id = id
    self.mpos = mpos
    self.wpos = wpos

  def __str__(self):
    return "<%s,MPos=%s,WPos=%s>" % (state_names[self.id], self.mpos, self.wpos)


class GrblHost:
  """
  The GrblHost class provides a more user-friendly interface to the raw Grbl
  serial protocol.

  It has a simple send commands and poll/retrieve events interface.
  Commands that can be sent include gcode lines but also real-time commands
  like cycle start and feed feed_hold.

  It does some minimal state tracking, e.g. for check mode but does not 
  validate any gcode commands
  """

  def __init__(self, port):
    """create the host and open the associated serial ser_port
    """
    # params
    self.port = port
    # state
    self.grbl_version = None
    self.in_check_mode = False
    self.is_open = False

  def open(self):
    """open serial port and wait for Grbl firmware hello"""
    if self.is_open:
      raise GrblHostError("already open!")
    self.port.open()
    self.is_open = True
    self.reset()

  def close(self):
    """close serial port and shut down grbl host"""
    if not self.is_open:
      raise GrblHostError("not open!")
    self.port.close()
    self.is_open = False
    self.grbl_version = None

  def reset(self):
    """reset of state and wait for Grbl hello"""
    if not self.is_open:
      raise GrblHostError("not open!")        
    # reset own state
    self.grbl_version = None
    self.in_check_mode = False
    # wait for init
    self.port.write("\x18") # ctrl-x = soft-reset
    self._wait_reset()
      
  def _wait_reset(self):
    """wait for reset in Grbl"""
    line = self.port.read_line(timeout=2)      
    if line is None:
      raise GrblHostError("reset failed!")
    # skip empty line
    if line == "":
      line = self.port.read_line(timeout=2)
    m = re.search("^Grbl (\d)\.(\d)(.)", line)
    if m is None:
      raise GrblHostError("no hello after reset: "+line)
    self.grbl_version = (m.group(1), m.group(2), m.group(3))

  # ----- get firmware release ----

  def get_firmware_version(self):
    """return firmware release"""
    return self.grbl_version

  # ----- toggle check mode -----

  def toggle_check_mode(self):
    # send command
    self.port.write("$C\r")
    # get state
    e = self.read_event()
    if e.id != ID_INFO:
      raise GrblEventError(e)
    state = e.data
    if state == 'Enabled':
      self.in_check_mode = True
    elif state == 'Disabled':
      self.in_check_mode = False
    else:
      raise GrblHostError("Invalid check_mode state: " + state)
    # get ok
    e = self.read_event()
    if e.id != ID_OK:
      raise GrblEventError(e)
    # wait for Grbl soft-reset after disable
    if not self.in_check_mode:
      self._wait_reset()

  def is_check_mode_enabled(self):
    """return true if check mode was enabled"""
    return self.in_check_mode

  # --- send commands ---

  def send_line(self, line):
    """send a line of GCode"""
    self.port.write(line + "\r")

  def send_kill_alarm(self):
    self.port.write("$X\r")

  def send_start_homing(self):
    self.port.write("$H\r")

  # ---- real time commands ----

  def send_cycle_start(self):
    self.port.write("~")

  def send_feed_hold(self):
    self.port.write("!")

  def send_request_state(self):
    self.port.write("?")

  # ---- grbl events ----

  def can_read_event(self, timeout=None):
    """poll if an event is ready to be read"""
    return self.port.can_read_line(timeout)

  def read_event(self, timeout=None):
    """read the next line of grbl output and parse it
       returns an event or None on timeout
    """
    # ignore empty lines
    line = ""
    while line == "":
      line = self.port.read_line(timeout)
      if line is None:
        return None
    # parse line
    line = line.strip()
    if len(line) > 1:
      if line == 'ok':
        return GrblEvent(ID_OK)
      elif line.startswith('error:'):
        return GrblEvent(ID_ERROR, line[6:])
      elif line.startswith('ALARM:'):
        return GrblEvent(ID_ALARM, line[6:])
      elif line[0] == '[' and line[-1] == ']':
        return GrblEvent(ID_INFO, line[1:-1]) 
      elif line[0] == '<' and line[-1] == '>':
        s = self._parse_state(line[1:-1])
        return GrblEvent(ID_STATE, s)

    raise GrblHostError("Invalid event text: "+line)

  def _parse_state(self, input):
    elem = input.split(',')
    if len(elem) < 7:
      raise GrblHostError("Too few state elements: "+input)
    # parse state
    state = self._parse_state_mode(elem[0])
    # check for machine and work pos
    mpos = self._parse_pos('MPos', elem[1:4])
    wpos = self._parse_pos('WPos', elem[4:7])
    return GrblState(state, mpos, wpos)

  def _parse_pos(self, tag, elem):
    # make sure tag matches
    if not elem[0].startswith(tag + ":"):
      raise GrblHostError("Invalid " + tag + " position text: " + elem[0])
    # strip tag
    elem[0] = elem[0][len(tag)+1:]
    return (float(elem[0]),
            float(elem[1]),
            float(elem[2]))

  def _parse_state_mode(self, s):
    if s == 'Idle':
      return STATE_IDLE
    elif s == 'Queue':
      return STATE_QUEUED
    elif s == 'Run':
      return STATE_CYCLE
    elif s == 'Hold':
      return STATE_HOLD
    elif s == 'Home':
      return STATE_HOME
    elif s == 'Alarm':
      return STATE_ALARM
    elif s == 'Check':
      return STATE_CHECK
    else:
      raise GrblHostError("Invalid state mode: "+s)
