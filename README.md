# 🕸️ NetPuppet - Remote Access Trojan (RAT) & Offensive Exfiltration Tool

**NetPuppet** is an offensive-oriented Remote Access Trojan (RAT) and Command & Control (C2) framework built in Python. 

The tool is designed to mimic real-world threat actor behaviors: once the agent (Trojan Horse) is executed on a target machine, it bypasses basic local constraints, initiates a stealthy reverse connection back to the attacker's server, and opens a direct pipeline for total remote control and automated data exfiltration.

---

### ⚠️ LABORATORY WARNING
> **This repository contains functional offensive software.**
> NetPuppet was developed strictly for research, defensive engineering analysis, and laboratory testing inside isolated virtual environments. Unauthorized deployment on networks or systems you do not own is illegal.

---

## 💥 Offensive Capabilities & Data Exfiltration Mechanics

NetPuppet acts as a persistent backdoor, enabling the attacker to silently harvest and exfiltrate information through several vector pipelines:

* **Automated Data Harvesting (Theft/Exfiltration):**
  * **Global Keylogging:** Silently monitors and logs keystrokes (supporting full English and Hebrew translations) to capture credentials and typed data.
  * **Surveillance (Screen & Video Capture):** Extracts real-time desktop screenshots and webcam video frames directly from the hardware, compressing and sending them over TCP.
  * **Targeted File Exfiltration:** Commands like `download` and `zip` allow the attacker to zip entire target directories and exfiltrate raw files from the victim's hard drive to the server.
  
* **Stealth and Anti-Forensics (Self-Destruct):**
  * Features a **Silent Self-Destruct (`terminate_all`)** protocol. Upon receiving the command, the agent cleans up its Startup persistence folder, drops active TCP connections, and spawns a background, windowless subprocess to permanently delete the executable file from the host's disk.

* **Victim System Manipulation:**
  * Allows execution of remote shell commands via subprocess spawning, directory traversal (`cd`), popping up uncloseable locked warning boxes (ransomware simulation), and forcing the target browser to open designated URLs.
