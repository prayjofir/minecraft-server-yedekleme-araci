import os
import shutil
import time
import threading
import tkinter as tk
from tkinter import messagebox, filedialog
from datetime import datetime, timedelta
import requests

CONFIG_FILE = "config.txt"

# === AYARLAR ===
WORLD_DIR = ""
BACKUP_DIR = ""
WEBHOOK_URL = ""  # Webhook URL'si başlangıçta boş

# Ayarları config.txt dosyasına yaz
def write_config():
    with open(CONFIG_FILE, "w") as f:
        f.write(f"{WORLD_DIR}\n")
        f.write(f"{BACKUP_DIR}\n")
        f.write(f"{WEBHOOK_URL}\n")

# Discord mesaj gönderme fonksiyonu
def send_discord_message(content):
    if WEBHOOK_URL:
        try:
            requests.post(WEBHOOK_URL, json={"content": content})
        except Exception as e:
            print("Discord bildirim hatası:", e)

# Yedekleme işlemi
def create_backup():
    try:
        timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
        backup_path = os.path.join(BACKUP_DIR, f"world_{timestamp}")
        shutil.copytree(WORLD_DIR, backup_path, dirs_exist_ok=True)
        print("[OK] Yedekleme tamamlandı:", backup_path)
        send_discord_message(f"✅ Yedekleme tamamlandı:\nDosya Yolu: {backup_path}\nZaman: {timestamp}")
        return backup_path
    except Exception as e:
        error_message = f"Yedekleme hatası: {e}\nKlasör: {WORLD_DIR}\nYedekleme Hedefi: {backup_path}"
        print(error_message)
        send_discord_message(f"❌ Yedekleme hatası: {error_message}")
        return None

# Eski yedekleri silme işlemi
def delete_old_backups(days=2):
    try:
        now = datetime.now()
        deleted_any = False
        for folder in os.listdir(BACKUP_DIR):
            path = os.path.join(BACKUP_DIR, folder)
            if os.path.isdir(path):
                folder_timestamp = folder.split('_')[-1]
                try:
                    folder_time = datetime.strptime(folder_timestamp, "%Y-%m-%d_%H-%M-%S")
                    if now - folder_time > timedelta(days=days):
                        shutil.rmtree(path)
                        print("Eski yedek silindi:", path)
                        deleted_any = True
                except Exception as e:
                    print(f"[X] Eski yedek silinirken hata oluştu: {e}")
        return deleted_any
    except Exception as e:
        print(f"[X] Yedekleri silerken hata oluştu: {e}")
        return False

class BackupApp:
    def __init__(self, master):
        self.master = master
        self.running = False
        self.interval_minutes = 30

        master.title("Minecraft Yedekleme")
        master.geometry("400x400")

        self.status = tk.Label(master, text="Durum: Beklemede", fg="blue")
        self.status.pack(pady=10)

        self.interval_label = tk.Label(master, text="Yedekleme Aralığı (dakika):")
        self.interval_label.pack()
        self.interval_entry = tk.Entry(master)
        self.interval_entry.insert(0, "30")
        self.interval_entry.pack(pady=5)

        self.start_btn = tk.Button(master, text="Otomatik Yedeklemeyi Başlat", command=self.start_backup)
        self.start_btn.pack(pady=5)

        self.stop_btn = tk.Button(master, text="Otomatik Yedeklemeyi Durdur", command=self.stop_backup, state=tk.DISABLED)
        self.stop_btn.pack(pady=5)

        self.manual_btn = tk.Button(master, text="Manuel Yedekleme", command=self.manual_backup)
        self.manual_btn.pack(pady=5)

        self.delete_btn = tk.Button(master, text="Eski Yedekleri Sil", command=self.delete_old_backups)
        self.delete_btn.pack(pady=5)

        self.delete_days_label = tk.Label(master, text="Eski Yedekleri Sil (gün sayısı):")
        self.delete_days_label.pack()
        self.delete_days_entry = tk.Entry(master)
        self.delete_days_entry.insert(0, "2")
        self.delete_days_entry.pack(pady=5)

        self.open_btn = tk.Button(master, text="Yedek Klasörünü Aç", command=self.open_backup_folder)
        self.open_btn.pack(pady=5)

        self.last_backup_label = tk.Label(master, text="Son Yedekleme: Henüz yapılmadı")
        self.last_backup_label.pack(pady=5)

    def open_backup_folder(self):
        try:
            os.startfile(BACKUP_DIR)
        except Exception as e:
            messagebox.showerror("Hata", f"Klasör açılamadı:\n{e}")

    def update_last_backup_time(self):
        self.last_backup_label.config(text=f"Son Yedekleme: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    def start_backup(self):
        try:
            self.interval_minutes = int(self.interval_entry.get())
        except ValueError:
            messagebox.showerror("Hata", "Lütfen geçerli bir sayı girin.")
            return

        self.running = True
        self.status.config(text="Durum: Otomatik yedekleme aktif", fg="green")
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.thread = threading.Thread(target=self.backup_loop)
        self.thread.daemon = True
        self.thread.start()

    def stop_backup(self):
        self.running = False
        self.status.config(text="Durum: Durduruldu", fg="red")
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)

    def backup_loop(self):
        while self.running:
            backup_path = create_backup()
            if backup_path:
                self.update_last_backup_time()
            for _ in range(self.interval_minutes * 60):
                if not self.running:
                    break
                time.sleep(1)

    def manual_backup(self):
        create_backup()

    def delete_old_backups(self):
        try:
            days_to_delete = int(self.delete_days_entry.get())
            if days_to_delete <= 0:
                messagebox.showerror("Hata", "Lütfen geçerli bir gün sayısı girin.")
                return
            deleted_any = delete_old_backups(days=days_to_delete)
            if deleted_any:
                messagebox.showinfo("Başarılı", f"{days_to_delete} günden eski yedekler başarıyla silindi.")
            else:
                messagebox.showinfo("Bilgi", f"{days_to_delete} günden eski yedek bulunamadı.")
        except ValueError:
            messagebox.showerror("Hata", "Lütfen geçerli bir sayı girin.")

class ConfigApp:
    def __init__(self, master):
        self.master = master
        self.master.title("Ayarları Yapılandır")
        self.master.geometry("400x350")

        self.world_dir_label = tk.Label(master, text="Dünya Klasörü:")
        self.world_dir_label.pack(pady=5)
        self.world_dir_entry = tk.Entry(master, width=40)
        self.world_dir_entry.pack(pady=5)
        self.world_dir_button = tk.Button(master, text="Klasör Seç", command=self.select_world_dir)
        self.world_dir_button.pack(pady=5)

        self.backup_dir_label = tk.Label(master, text="Yedekleme Klasörü:")
        self.backup_dir_label.pack(pady=5)
        self.backup_dir_entry = tk.Entry(master, width=40)
        self.backup_dir_entry.pack(pady=5)
        self.backup_dir_button = tk.Button(master, text="Klasör Seç", command=self.select_backup_dir)
        self.backup_dir_button.pack(pady=5)

        self.webhook_label = tk.Label(master, text="Discord Webhook URL (Opsiyonel):")
        self.webhook_label.pack(pady=5)
        self.webhook_entry = tk.Entry(master, width=40)
        self.webhook_entry.pack(pady=5)

        self.save_btn = tk.Button(master, text="Kaydet ve Yedekleme Penceresini Aç", command=self.save_settings)
        self.save_btn.pack(pady=20)

        self.load_config()

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    lines = f.readlines()
                    if len(lines) >= 2:
                        self.world_dir_entry.insert(0, lines[0].strip())
                        self.backup_dir_entry.insert(0, lines[1].strip())
                        if len(lines) > 2:
                            self.webhook_entry.insert(0, lines[2].strip())
            except Exception as e:
                messagebox.showerror("Hata", f"Config dosyasını okurken hata oluştu: {e}")

    def select_world_dir(self):
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.world_dir_entry.delete(0, tk.END)
            self.world_dir_entry.insert(0, folder_selected)
        else:
            messagebox.showerror("Hata", "Geçerli bir klasör seçmelisiniz.")

    def select_backup_dir(self):
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.backup_dir_entry.delete(0, tk.END)
            self.backup_dir_entry.insert(0, folder_selected)
        else:
            messagebox.showerror("Hata", "Geçerli bir klasör seçmelisiniz.")

    def save_settings(self):
        global WORLD_DIR, BACKUP_DIR, WEBHOOK_URL
        WORLD_DIR = self.world_dir_entry.get()
        BACKUP_DIR = self.backup_dir_entry.get()
        WEBHOOK_URL = self.webhook_entry.get().strip()

        if not WORLD_DIR or not BACKUP_DIR:
            messagebox.showerror("Hata", "Lütfen dünya ve yedekleme klasörünü seçin.")
            return

        if not os.path.exists(BACKUP_DIR):
            try:
                os.makedirs(BACKUP_DIR)
            except Exception as e:
                messagebox.showerror("Hata", f"Yedekleme klasörü oluşturulamadı: {e}")
                return

        write_config()
        messagebox.showinfo("Başarılı", "Ayarlar kaydedildi.")

        self.master.destroy()
        self.master.quit()
        self.open_backup_window()

    def open_backup_window(self):
        root = tk.Tk()
        app = BackupApp(root)
        root.mainloop()

if __name__ == "__main__":
    root = tk.Tk()
    app = ConfigApp(root)
    root.mainloop()