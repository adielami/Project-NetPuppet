# 🕸️ NetPuppet - Advanced E2E Command & Control (C2) Framework

**NetPuppet** is a custom-built, full-fledged Command and Control (C2) framework and Remote Administration Tool developed in Python. 

This project was architected from the ground up to research and demonstrate low-level network communication (TCP sockets), data framing, persistence mechanisms, and operating system API interactions.

### ⚠️ IMPORTANT DISCLAIMER: STRICTLY FOR LABORATORY USE
> **This tool was developed EXCLUSIVELY for educational purposes and cybersecurity research.** > It is designed to be executed **only within closed, isolated laboratory environments** (e.g., isolated VMs or local loopback interfaces). The author assumes no liability for any unauthorized use. Do not deploy this on systems without explicit, documented permission.

---

## 🛠️ System Architecture & Technical Highlights

Unlike basic reverse shells, NetPuppet handles common networking and synchronization challenges directly:
* **TCP Stream Coalescence Prevention:** Implements custom data framing using `struct.pack` to transmit payload sizes ahead of data, ensuring distinct command execution without packet fusion.
* **Multithreaded Execution:** Utilizes Python's `threading` to run blocking GUI operations (like ransomware-style popups) and global keyboard hooks without interrupting the main socket communication loop.
* **Smart Keylogger Engine:** Includes layout-awareness (Hebrew/English translation logic) and handles shortcut combinations (Ctrl/Alt), avoiding application crashes during hook registration.
* **Stealth & Persistence:** Modifies the Windows Startup folder for persistence and includes a silent, self-destruct mechanism that terminates the process, removes startup artifacts, and deletes the executable via hidden OS subprocesses.

---

## 🚀 How to Operate the Lab Environment

To test the C2 communication safely on a local machine:

1. **Start the Listener (Server):**
   Open a terminal and execute the server script. It will bind to `0.0.0.0` (or your configured `HOST_IP`) on port `9998` and wait for incoming connections.
   ```bash
   python server.py
