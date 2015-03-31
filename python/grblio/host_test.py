# unittests for grblhost

import os
import unittest
import glob
import time

import host
import serport
import tcpport

ser_port = os.path.expanduser("~/grbl-serial")
if os.path.exists(ser_port):
  port = serport.SerPort(ser_port)
else:
  port = tcpport.TcpPort("pibox")

class GrblHostBaseTests(unittest.TestCase):
  def setUp(self):
    self.host = host.GrblHost(port)

  def testOpenClose(self):
    # no version yet
    self.assertIsNone(self.host.get_firmware_version())
    # open
    self.host.open()
    # make sure we have a version
    self.assertIsNotNone(self.host.get_firmware_version())
    # assume there is no event waiting
    self.assertFalse(self.host.can_read_event(0.1))
    # close
    self.host.close()
    # no version again
    self.assertIsNone(self.host.get_firmware_version())

  def testOpenCloseErrors(self):
    # close before open is not allowed
    with self.assertRaises(host.GrblHostError):
        self.host.close()
    # open
    self.host.open()
    # double open is not allowed
    with self.assertRaises(host.GrblHostError):
        self.host.open()
    # close
    self.host.close()

  def testReset(self):
    # not allowed before open
    with self.assertRaises(host.GrblHostError):
        self.host.reset()
    # open
    self.host.open()
    # hard reset
    self.host.reset()
    # assume there is no event waiting
    self.assertFalse(self.host.can_read_event(0.1))
    # close
    self.host.close()
    # not allowed after close     
    with self.assertRaises(host.GrblHostError):
        self.host.reset()


class GrblHostTests(unittest.TestCase):
  def setUp(self):
    self.host = host.GrblHost(port)
    self.host.open()

  def tearDown(self):
    self.host.close()

  def testReset(self):
    self.host.reset()

  def testCheckMode(self):
    # assume its disabled
    self.assertFalse(self.host.is_check_mode_enabled())
    # now enable it
    self.host.toggle_check_mode()
    # assume its enabled
    self.assertTrue(self.host.is_check_mode_enabled())
    # now disable it
    self.host.toggle_check_mode()
    # assume its disable again
    self.assertFalse(self.host.is_check_mode_enabled())

  def testStateEvent(self):
    self.host.send_request_state()
    e = self.host.read_event()
    self.assertEqual(host.ID_STATE, e.id)
    s = e.data
    # make sure result is a GrblState
    self.assertEqual(host.GrblState, s.__class__)

  def testSendLine(self):
    # assume no event is waiting
    self.assertFalse(self.host.can_read_event())
    # send some gcode
    gcode = "G0 X1 Y2 Z3"
    self.host.send_line(gcode)
    # get state event (block until op is finished)
    e = self.host.read_event()
    self.assertEqual(host.ID_OK, e.id)
    # wait until idle again
    t = time.time() + 10
    while time.time() < t:
      self.host.send_request_state()
      e = self.host.read_event(1)
      s = e.data
      if s.id == host.STATE_IDLE:
        break
      time.sleep(1)
    # update state
    self.host.send_request_state()
    e = self.host.read_event()
    s = e.data
    self.assertEqual((1.0, 2.0, 3.0), s.wpos)
    self.assertEqual((1.0, 2.0, 3.0), s.mpos)


if __name__ == '__main__':
  unittest.main(verbosity=2)
