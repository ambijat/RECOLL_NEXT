/* Copyright (C) 2016 J.F.Dockes
 *   This program is free software; you can redistribute it and/or modify
 *   it under the terms of the GNU Lesser General Public License as published by
 *   the Free Software Foundation; either version 2.1 of the License, or
 *   (at your option) any later version.
 *
 *   This program is distributed in the hope that it will be useful,
 *   but WITHOUT ANY WARRANTY; without even the implied warranty of
 *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *   GNU Lesser General Public License for more details.
 *
 *   You should have received a copy of the GNU Lesser General Public License
 *   along with this program; if not, write to the
 *   Free Software Foundation, Inc.,
 *   51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
 */
#ifndef _CMDTALK_H_INCLUDED_
#define _CMDTALK_H_INCLUDED_

/** 
 * Execute commands and exchange messages with it.
 *
 * A simple stream protocol is used for the dialog. HTTP or some kind
 * of full-blown RPC could have been used, but there was also good
 * reason to keep it simple (yet powerful), given the limited context
 * of dialog through a pipe.
 *
 * The data is exchanged in TLV fashion, in a way that should be
 * usable in most script languages. The basic unit of data has one line 
 * with a data type and a count (both ASCII), followed by the data. A
 * 'message' is made of one or several units or tags and ends with one empty
 * line. 
 * 
 * Example:(the message begins before 'Filename' and has 'Filename' and 
 * 'Ipath' tags):
 * 
Filename: 24
/my/home/mail/somefolderIpath: 2
22

<Message ends here: because of the empty line after '22'

 * 
 * Example answer, with 'Mimetype' and 'Data' tags
 * 
Mimetype: 10
text/plainData: 10
0123456789

<Message ends here because of empty line

 *        
 * This format is both extensible and reasonably easy to parse. 
 * While it's more fitted for python or perl on the script side, it
 * should even be sort of usable from the shell (e.g.: use dd to read
 * the counted data). Most alternatives would need data encoding in
 * some cases.
 *
 * Higher level dialog:
 * The C++ program is the master and sends request messages to the script. 
 * Both sides of the communication should be prepared to receive and discard 
 * unknown tags.
 */

#include <string>
#include <vector>
#include <unordered_map>

/**
 * C++ Master/Client implementation of the CmdTalk IPC/RPC protocol.
 * Manages spawning a persistent subprocess (using ExecCmd) and handles
 * bidirectional key-value stream exchange.
 */
class CmdTalk {
 public:
    /**
     * Constructor.
     * @param timeosecs Timeout in seconds. If the child process takes longer
     *                  than this limit to read/write, a timeout exception is
     *                  triggered and the child process is terminated.
     */
    CmdTalk(int timeosecs);
    virtual ~CmdTalk();

    // Disable copy constructor and assignment operator to prevent double-free
    // of the Pimpl instance.
    CmdTalk(const CmdTalk&) = delete;
    CmdTalk& operator=(const CmdTalk&) = delete;

    /**
     * Spawns the helper subprocess command.
     * 
     * @param cmdname Name or path of the executable command to run.
     * @param args Command-line arguments to pass to the command.
     * @param env Subprocess environment variables (each entry formatted as "NAME=VALUE").
     * @param path Custom search path directories to locate cmdname.
     * 
     * @return True if the process successfully started, false otherwise.
     */
    virtual bool startCmd(const std::string& cmdname,
              const std::vector<std::string>& args =
              std::vector<std::string>(),
              const std::vector<std::string>& env =
              std::vector<std::string>(),
              const std::vector<std::string>& path =
              std::vector<std::string>()
    );

    /**
     * Checks if the subprocess is currently running.
     * 
     * @return True if the subprocess is active, false if it has exited or failed.
     */
    virtual bool running();
    
    /**
     * Performs a single synchronous request-response exchange.
     * Serializes args map to stdin pipe, flushes, and reads the child's response
     * from stdout pipe until the empty line boundary is reached.
     * 
     * @param args Key-value map of parameters to send to the child.
     * @param rep Key-value map to store the child's response parameters.
     * 
     * @return True if exchange was successful, false if process failed/timed out,
     *         or if 'cmdtalkstatus' error parameter was returned by the child.
     */
    virtual bool talk(const std::unordered_map<std::string, std::string>& args,
              std::unordered_map<std::string, std::string>& rep);

    /**
     * Invokes a specific RPC method on the helper subprocess.
     * Convenience wrapper around talk() that inserts a "cmdtalk:proc" parameter.
     * 
     * @param proc The name of the procedure/method to invoke.
     * @param args Key-value map of parameters to send.
     * @param rep Key-value map to populate with response parameters.
     * 
     * @return True on success, false on failure or error.
     */
    virtual bool callproc(
    const std::string& proc,
    const std::unordered_map<std::string, std::string>& args,
    std::unordered_map<std::string, std::string>& rep);

private:
    class Internal;
    Internal *m{0}; // Pointer to implementation (Pimpl pattern) to keep headers clean.
};

#endif /* _CMDTALK_H_INCLUDED_ */
