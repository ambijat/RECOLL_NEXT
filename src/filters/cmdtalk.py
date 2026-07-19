#################################
# Copyright (C) 2016 J.F.Dockes
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation; either version 2 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program; if not, write to the
#   Free Software Foundation, Inc.,
#   51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
########################################################
# Command communication module and utilities. See commands in cmdtalk.h
#
# All data is binary. This is important for Python3
# All parameter names are converted to and processed as str/unicode

import sys
import os
import traceback
import signal
from typing import Any, Union, TextIO, BinaryIO, Text, AnyStr, Callable, Optional, Dict, Tuple


def makebytes(data: AnyStr) -> bytes:
    """Helper to convert unicode string to UTF-8 bytes.

    If input is already bytes, it returns it unchanged.
    """
    if data is None:
        return b""
    if isinstance(data, str):
        return data.encode("UTF-8")
    else:
        return data


def breakwrite(outfile: BinaryIO, data: bytes) -> None:
    """Writes binary data to the output stream.

    On Windows, writing large contiguous buffers (e.g. > 32KB) directly to
    stdout/pipes can fail with a 'not enough space' or pipe-ended error.
    This function avoids the issue by splitting the payload into small 4KB chunks
    and writing them sequentially.
    """
    if sys.platform != "win32":
        outfile.write(data)
    else:
        # On Windows, writing big chunks can fail with a "not enough space"
        # error. Seems a combined windows/python bug, depending on versions.
        # See https://bugs.python.org/issue11395
        # In any case, just break it up
        total = len(data)
        bs = 4 * 1024
        offset = 0
        while total > 0:
            if total < bs:
                tow = total
            else:
                tow = bs
            outfile.write(data[offset : offset + tow])
            offset += tow
            total -= tow


############################################
# CmdTalk implements the communication protocol with the master
# process. It calls an external method to use the args and produce
# return data.
class CmdTalk(object):
    """Implements the Python side of the CmdTalk protocol.

    It handles stream binary modes, reads and parses structured parameters
    from stdin, dispatches processing, and sends answers back to the stdout pipe.
    """

    def __init__(self, outfile: TextIO = sys.stdout, infile: TextIO = sys.stdin,
                 exitfunc: Optional[Callable] = None):
        """Initializes pipes and configures Windows binary stream mode if needed."""
        try:
            self.myname = os.path.basename(sys.argv[0])
        except:
            self.myname = "???"

        self.outfile = outfile
        self.infile = infile
        self.exitfunc = exitfunc

        # On Windows, stdin and stdout must be set to binary mode.
        # This prevents newline translation (\n <-> \r\n) and prevents
        # early EOF on Ctrl-Z (0x1A) byte characters.
        if sys.platform == "win32":
            import msvcrt
            msvcrt.setmode(self.outfile.fileno(), os.O_BINARY)
            msvcrt.setmode(self.infile.fileno(), os.O_BINARY)

        if not hasattr(self, 'debugfile'):
            self.debugfile = None
        if not hasattr(self, 'nodecodeinput'):
            self.nodecodeinput = False
        self.errfout: TextIO = sys.stderr
        if self.debugfile:
            self.errfout: TextIO = open(self.debugfile, "a")

    def log(self, s: AnyStr, doexit: int = 0, exitvalue: int = 1) -> None:
        """Logs a debug/error message to stderr or log file, and optionally exits."""
        print(f"CMDTALK: {self.myname}: {s!r}", file=self.errfout)
        if doexit:
            if self.exitfunc:
                self.exitfunc(exitvalue)
            sys.exit(exitvalue)

    # Read single parameter from process input: line with param name and size
    # followed by data. The param name is returned as str/unicode, the data
    # as bytes or str, depending on the nodecodeinput option.
    def readparam(self) -> Tuple[Text, Union[bytes, str]]:
        """Reads a single key-value parameter from standard input.

        Expects a line containing '<paramname>: <size>\n' followed by exactly
        <size> bytes of value data.

        Returns:
            A tuple of (paramname, paramvalue), where paramvalue is decoded to str/unicode
            unless nodecodeinput is enabled.
            If the end of the current message is reached (an empty line '\n'), returns ("", b"").
        """
        inf = self.infile.buffer
        s = inf.readline()
        if s == b"":
            # Empty read indicates stdin is closed (parent process terminated)
            if self.exitfunc:
                self.exitfunc(0)
            # Our father process is probably going to send us a SIGTERM.  On some platforms (BSD,
            # MacOS), an exception is sometimes generated during exit processing, probably randomly
            # depending on where we are in the process when we receive the signal. Ignoring SIGTERM
            # while we exit mostly fixes the problem (we very rarely get a message about a signal
            # race condition). None of this affects the working of the program anyway, just an issue
            # with error messages.
            signal.signal(signal.SIGTERM, signal.SIG_IGN)
            sys.exit(0)

        s = s.rstrip(b"\n")

        if s == b"":
            return ("", b"")
        l = s.split()
        if len(l) != 2:
            self.log(b"bad line: [" + s + b"]", 1, 1)

        paramname = l[0].decode("ASCII").rstrip(":")
        paramsize = int(l[1])
        if paramsize > 0:
            paramdata = inf.read(paramsize)
            if len(paramdata) != paramsize:
                self.log(
                    "Bad read: wanted %d, got %d" % (paramsize, len(paramdata)), 1, 1
                )
        else:
            paramdata = b""
        if not self.nodecodeinput:
            try:
                paramstr: str = paramdata.decode("utf-8")
                return (paramname, paramstr)
            except Exception as ex:
                self.log("Exception decoding param: %s" % ex)
                paramdata = b""

        # self.log("paramname [%s] paramsize %d value [%s]" %
        #          (paramname, paramsize, paramdata))
        return (paramname, paramdata)

    def senditem(self, nm: Text, _data: AnyStr) -> None:
        """Sends a single key-value parameter back to the master process stdout."""
        data: bytes = makebytes(_data)
        l = len(data)
        self.outfile.buffer.write(makebytes("%s: %d\n" % (nm, l)))
        breakwrite(self.outfile.buffer, data)

    # Send answer
    def answer(self, outfields: Dict[Text, AnyStr]) -> None:
        """Sends a dictionary of output fields as a complete response message.

        Each dictionary item is sent as a separate key-value parameter,
        followed by a final empty line to terminate the message framing.
        """
        for nm, value in outfields.items():
            # self.log("Senditem: [%s] -> [%s]" % (nm, value))
            self.senditem(nm, value)

        # End of message: empty line
        print(file=self.outfile)
        self.outfile.flush()
        # self.log("done writing data")

    # Call processor with input params, send result. This base version works with, for example
    # the cmdtalkplugin processor.
    def processmessage(self, processor, params: Dict[Text, Union[bytes, str]]) -> None:
        """Invokes the processor's process method to handle the parameters.

        Sends the generated response fields back. Handles exceptions gracefully by
        returning cmdtalkstatus and error description parameters.
        """
        # In normal usage we try to recover from processor errors, but
        # we sometimes want to see the real stack trace when testing
        safeexec = True
        if safeexec:
            try:
                outfields = processor.process(params)
            except Exception as err:
                self.log("processmessage: processor raised: [%s]" % err)
                traceback.print_exc()
                outfields = {}
                outfields["cmdtalkstatus"] = "1"
                outfields["cmdtalkerrstr"] = str(err)
        else:
            outfields = processor.process(params)

        self.answer(outfields)

    # Loop on messages from our master
    def mainloop(self, processor: Any) -> None:
        """Loops continuously, reading requests and processing messages.

        Stops reading a message when an empty parameter name is returned (empty line).
        """
        while 1:
            # self.log("waiting for command")
            params = dict()

            # Read at most 20 parameters (normally 1 or 2), stop at empty line
            # End of message is signalled by empty paramname
            for i in range(20):
                paramname, paramdata = self.readparam()
                if paramname == "":
                    break
                params[paramname] = paramdata

            # Got message, act on it
            self.processmessage(processor, params)


# Common main routine for testing: either run the normal protocol
# engine or a local loop. This means that you can call
# cmdtalk.main(proto,processor) instead of proto.mainloop(processor)
# from your module, and get the benefits of command line testing
def main(proto: CmdTalk, processor: Any) -> None:
    """Helper entry point for testing and execution.

    If run without arguments, launches the normal persistent protocol mainloop.
    If run with arguments, parses the command-line arguments as key-value pairs,
    runs the processor once, writes the raw results to stdout, and exits.
    """
    if len(sys.argv) == 1:
        proto.mainloop(processor)
        # mainloop does not return. Just in case
        sys.exit(1)

    # Not running the main loop: run one processor call for debugging
    def usage():
        print("Usage: cmdtalk.py pname pvalue [pname pvalue...]", file=sys.stderr)
        sys.exit(1)

    def debprint(out, s):
        breakwrite(out, makebytes(s + "\n"))

    args = sys.argv[1:]
    if len(args) == 0 or len(args) % 2 != 0:
        usage()
    params = dict()
    for i in range(int(len(args) / 2)):
        params[args[2 * i]] = args[2 * i + 1]
    res = processor.process(params)

    ioout = sys.stdout.buffer

    for nm, value in res.items():
        # debprint(f"Senditem: [{nm}] -> [{value}]")
        bdata = makebytes(value)
        debprint(ioout, "%s->" % nm)
        breakwrite(ioout, bdata)
        ioout.write(b"\n")
