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
WEBHOOK_URL = ""

# Ayarları config.txt dosyasına yaz
def write_config():
    with open(CONFIG_FILE, "w") as f:
        f.write(f"{WORLD_DIR}\n")
        f.write(f"{BACKUP_DIR}\n")
        f.write(f"{WEBHOOK_URL}\n" if WEBHOOK_URL else "\n")

# Discord mesaj gönderme
def send_discord_message(content):
    if WEBHOOK_URL:
        try:
            requests.post(WEBHOOK_URL, json={"content": content})
        except Exception as e:
            print("Discord bildirim hatası:", e)

# Yedekleme işlemi (session.lock hariç)
def create_backup():
    try:
        timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
        backup_path = os.path.join(BACKUP_DIR, f"world_{timestamp}")

        def ignore_files(dir, files):
            return ['session.lock'] if 'session.lock' in files else []

        shutil.copytree(WORLD_DIR, backup_path, dirs_exist_ok=True, ignore=ignore_files)
        print("[OK] Yedekleme tamamlandı:", backup_path)
        send_discord_message(f"✅ Yedekleme tamamlandı:\n📁 {backup_path}\n🕒 {timestamp}")
        return backup_path
    except Exception as e:
        error_message = f"Yedekleme hatası: {e}"
        print(error_message)
        send_discord_message(f"❌ {error_message}")
        return None

# Eski yedekleri sil
def delete_old_backups(days=2):
    try:
        now = datetime.now()
        deleted_any = False
        for folder in os.listdir(BACKUP_DIR):
            path = os.path.join(BACKUP_DIR, folder)
            if os.path.isdir(path):
                try:
                    timestamp = folder.split('_')[-1]
                    folder_time = datetime.strptime(timestamp, "%Y-%m-%d_%H-%M-%S")
                    if now - folder_time > timedelta(days=days):
                        shutil.rmtree(path)
                        print("Eski yedek silindi:", path)
                        deleted_any = True
                except Exception as e:
                    print("Tarih ayrıştırma hatası:", e)
        return deleted_any
    except Exception as e:
        print("Yedek silme hatası:", e)
        return False

# Yedekleme uygulaması GUI
class BackupApp:
    def __init__(self, master):
        self.master = master
        self.running = False
        self.interval_minutes = 30

        master.title("Minecraft Yedekleme")
        master.geometry("400x420")

        self.status = tk.Label(master, text="Durum: Beklemede", fg="blue")
        self.status.pack(pady=10)

        tk.Label(master, text="Yedekleme Aralığı (dakika):").pack()
        self.interval_entry = tk.Entry(master)
        self.interval_entry.insert(0, "30")
        self.interval_entry.pack(pady=5)

        self.start_btn = tk.Button(master, text="Otomatik Yedeklemeyi Başlat", command=self.start_backup)
        self.start_btn.pack(pady=5)

        self.stop_btn = tk.Button(master, text="Otomatik Yedeklemeyi Durdur", command=self.stop_backup, state=tk.DISABLED)
        self.stop_btn.pack(pady=5)

        self.manual_btn = tk.Button(master, text="Manuel Yedekleme", command=self.manual_backup)
        self.manual_btn.pack(pady=5)

        tk.Label(master, text="Eski Yedekleri Sil (gün):").pack()
        self.delete_days_entry = tk.Entry(master)
        self.delete_days_entry.insert(0, "2")
        self.delete_days_entry.pack(pady=5)

        self.delete_btn = tk.Button(master, text="Eski Yedekleri Sil", command=self.delete_old_backups)
        self.delete_btn.pack(pady=5)

        self.open_btn = tk.Button(master, text="Yedek Klasörünü Aç", command=self.open_backup_folder)
        self.open_btn.pack(pady=5)

        self.last_backup_label = tk.Label(master, text="Son Yedekleme: Henüz yapılmadı")
        self.last_backup_label.pack(pady=10)

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
        threading.Thread(target=self.backup_loop, daemon=True).start()

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
        backup_path = create_backup()
        if backup_path:
            self.update_last_backup_time()

    def delete_old_backups(self):
        try:
            days = int(self.delete_days_entry.get())
            if days <= 0:
                raise ValueError
            deleted = delete_old_backups(days=days)
            msg = "Eski yedekler silindi." if deleted else "Silinecek eski yedek bulunamadı."
            messagebox.showinfo("Bilgi", msg)
        except ValueError:
            messagebox.showerror("Hata", "Lütfen geçerli bir gün sayısı girin.")

# Ayar yapılandırma arayüzü
class ConfigApp:
    def __init__(self, master):
        self.master = master
        master.title("Ayarları Yapılandır")
        master.geometry("400x350")

        tk.Label(master, text="Dünya Klasörü:").pack()
        self.world_dir_entry = tk.Entry(master, width=40)
        self.world_dir_entry.pack(pady=5)
        tk.Button(master, text="Klasör Seç", command=self.select_world_dir).pack(pady=5)

        tk.Label(master, text="Yedekleme Klasörü:").pack()
        self.backup_dir_entry = tk.Entry(master, width=40)
        self.backup_dir_entry.pack(pady=5)
        tk.Button(master, text="Klasör Seç", command=self.select_backup_dir).pack(pady=5)

        tk.Label(master, text="Discord Webhook URL (Opsiyonel):").pack()
        self.webhook_entry = tk.Entry(master, width=40)
        self.webhook_entry.pack(pady=5)

        tk.Button(master, text="Kaydet ve Devam Et", command=self.save_settings).pack(pady=20)

        self.load_config()

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as f:
                lines = f.readlines()
                if len(lines) >= 2:
                    self.world_dir_entry.insert(0, lines[0].strip())
                    self.backup_dir_entry.insert(0, lines[1].strip())
                    if len(lines) > 2:
                        self.webhook_entry.insert(0, lines[2].strip())

    def select_world_dir(self):
        folder = filedialog.askdirectory()
        if folder:
            self.world_dir_entry.delete(0, tk.END)
            self.world_dir_entry.insert(0, folder)

    def select_backup_dir(self):
        folder = filedialog.askdirectory()
        if folder:
            self.backup_dir_entry.delete(0, tk.END)
            self.backup_dir_entry.insert(0, folder)

    def save_settings(self):
        global WORLD_DIR, BACKUP_DIR, WEBHOOK_URL
        WORLD_DIR = self.world_dir_entry.get()
        BACKUP_DIR = self.backup_dir_entry.get()
        WEBHOOK_URL = self.webhook_entry.get().strip()

        if not WORLD_DIR or not BACKUP_DIR:
            messagebox.showerror("Hata", "Lütfen tüm klasörleri belirtin.")
            return

        if not os.path.exists(BACKUP_DIR):
            try:
                os.makedirs(BACKUP_DIR)
            except Exception as e:
                messagebox.showerror("Hata", f"Yedek klasörü oluşturulamadı:\n{e}")
                return

        write_config()
        messagebox.showinfo("Başarılı", "Ayarlar kaydedildi.")
        self.master.destroy()
        open_backup_window()

def open_backup_window():
    root = tk.Tk()
    BackupApp(root)
    root.mainloop()

if __name__ == "__main__":
    root = tk.Tk()
    ConfigApp(root)
    root.mainloop()
