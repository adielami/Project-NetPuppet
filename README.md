# 🎭 NetPuppet - Remote Administration Tool (RAT)

**NetPuppet** is a lightweight Remote Administration Tool developed in Python.
This project was created for **educational purposes only** to demonstrate how malware operates, communicates, and controls systems remotely. Understanding these mechanisms is crucial for developing effective defense strategies and endpoint protection.

---

### ⚠️ Disclaimer
> **This tool is strictly for educational use and authorized testing on local networks.**
> The author is not responsible for any misuse or damage caused by this program. Do not use this tool on systems you do not own or have explicit permission to test.

---

## 🛠️ Technical Overview
The system consists of a **Server (Attacker)** and a **Client (Target)** that communicate over TCP/IP sockets. It demonstrates low-level networking concepts and system manipulation APIs.

### Key Features
* **Remote Shell Access:** Execute system commands (CMD/PowerShell) remotely and retrieve output.
* **Live Surveillance:**
    * **Keylogger:** Captures keystrokes in real-time to analyze user input patterns.
    * **Screen Capture:** Takes snapshots of the target's desktop.
    * **Webcam Control:** Captures images from the connected camera.
* **File Management:** Upload and download files between the attacker and target machines.
* **Persistence:** Mechanisms to maintain connection across system reboots (Educational demonstration).

## 💻 Tech Stack
* **Language:** Python 3.x
* **Networking:** Raw Sockets (TCP/IP)
* **Concurrency:** `threading` module for handling multiple tasks simultaneously (e.g., listening for commands while logging keys).
* **System APIs:** `subprocess`, `os`, `ctypes` (for interacting with Windows API).

## 🚀 How it Works
1.  **The Server** binds to a port and listens for incoming connections.
2.  **The Client** connects to the server's IP address.
3.  Once the handshake is complete, the Server sends commands (e.g., `<take_screenshot>`) which the Client interprets, executes, and returns the data.

## 🛡️ Security Perspective (Why I built this)
Building a RAT from scratch taught me:
* How antivirus software detects suspicious behavior (heuristic analysis).
* How network firewalls filter traffic based on ports and protocols.
* The importance of encrypting C&C traffic (to avoid detection by IDSs).
