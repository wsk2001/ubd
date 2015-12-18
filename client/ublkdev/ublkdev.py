from __future__ import absolute_import, print_function
from cStringIO import StringIO
import ctypes
import fcntl
import os
import select
import struct
from .ioctl import _IOR, _IOW, _IOWR

DISK_NAME_LEN = 32

UBD_IOCREGISTER = 0xc038bfa0
UBD_IOCUNREGISTER = 0xbfa1
UBD_IOCGETCOUNT = 0x8004bfa2
UBD_IOCDESCRIBE = 0xc040bfa3

UBD_FL_READ_ONLY = 0x00000001
UBD_FL_REMOVABLE = 0x00000002

class UBDInfo(ctypes.Structure):
    _fields_ = [
        ("ubd_name", ctypes.c_char * DISK_NAME_LEN),
        ("ubd_flags", ctypes.c_uint32),
        ("ubd_nsectors", ctypes.c_uint64),
        ("ubd_major", ctypes.c_uint32),
        ("ubd_minor", ctypes.c_uint32),
    ]

class UBDDescribe(ctypes.Structure):
    _fields_ = [
        ("ubd_index", ctypes.c_size_t),
        ("ubd_info", UBDInfo),
    ]

class UBDSectorsStatus(ctypes.Union):
    _fields_ = [
        ("ubd_nsectors", ctypes.c_uint32),
        ("ubd_status", ctypes.c_int32),
    ]

class UBDMessage(ctypes.Structure):
    _anonymous_ = ("ubd_secstat",)
    _fields_ = [
        ("ubd_msgtype", ctypes.c_uint32),
        ("ubd_tag", ctypes.c_uint32),
        ("ubd_secstat", UBDSectorsStatus),
        ("ubd_first_sector", ctypes.c_uint64),
        ("ubd_size", ctypes.c_uint32),
        ("ubd_data", ctypes.c_char_p),
    ]

UBD_MSGTYPE_READ = 0
UBD_MSGTYPE_WRITE = 1
UBD_MSGTYPE_DISCARD = 2

UBD_IOC_MAGIC = 0xaf
UBD_IOCREGISTER = _IOWR(UBD_IOC_MAGIC, 0xa0, ctypes.sizeof(UBDInfo))
UBD_IOCUNREGISTER = _IOWR(UBD_IOC_MAGIC, 0xa1, ctypes.sizeof(ctypes.c_int))
UBD_IOCGETCOUNT = _IOR(UBD_IOC_MAGIC, 0xa2, ctypes.sizeof(ctypes.c_int))
UBD_IOCDESCRIBE = _IOWR(UBD_IOC_MAGIC, 0xa3, ctypes.sizeof(UBDDescribe))
UBD_IOCTIE = _IOW(UBD_IOC_MAGIC, 0xa4, ctypes.sizeof(ctypes.c_int))
UBD_IOCGETREQUEST = _IOWR(UBD_IOC_MAGIC, 0xa5, ctypes.sizeof(UBDMessage))
UBD_IOCPUTREPLY = _IOW(UBD_IOC_MAGIC, 0xa6, ctypes.sizeof(UBDMessage))

UBD_FL_READ_ONLY = 0x00000001
UBD_FL_REMOVABLE = 0x00000002
    
class UserBlockDevice(object):
    def __init__(self, control_endpoint="/dev/ubdctl", buffer_size=65536):
        super(UserBlockDevice, self).__init__()
        self.control = os.open(control_endpoint, os.O_RDWR | os.O_SYNC |
                               os.O_NONBLOCK)
        self.in_poll = select.poll()
        self.in_poll.register(self.control, select.POLLIN)
        return

    def register(self, name, n_sectors, read_only=False):
        ubd_info = UBDInfo()
        ubd_info.ubd_name = name
        ubd_info.ubd_nsectors = n_sectors
        ubd_info.ubd_flags = UBD_FL_READ_ONLY if read_only else 0
        ubd_info.ubd_major = 0
        ubd_info.ubd_minor = 0

        fcntl.ioctl(self.control, UBD_IOCREGISTER, ubd_info)
        return

    def unregister(self, major):
        fcntl.ioctl(self.control, UBD_IOCUNREGISTER, ctypes.c_int(major))
        return

    @property
    def count(self):
        return fcntl.ioctl(self.control, UBD_IOCGETCOUNT)
        
    def describe(self, index):
        ubd_describe = UBDDescribe()
        ubd_describe.ubd_index = index
        fcntl.ioctl(self.control, UBD_IOCDESCRIBE, ubd_describe)
        return ubd_describe.ubd_info

    def get_request(self, buf):
        msg = UBDMessage()
        msg.ubd_data = buf
        fcntl.ioctl(self.control, UBD_IOCGETREQUEST, msg)
        return msg

    def put_reply(self, msg):
        fcntl.ioctl(self.control, UBD_IOCPUTREPLY, msg)
        return
