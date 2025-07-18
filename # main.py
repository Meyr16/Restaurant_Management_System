# main.py
import tkinter as tk
from tkinter import messagebox, ttk
from datetime import datetime, timedelta
import ds as ds  # Stelle sicher, dass ds_algos.py neben dieser Datei liegt

### NEU: Imports für serielle Kommunikation
import serial
import serial.tools.list_ports
import threading
import queue
import time # Für sleep im Thread

# ========================================
# Daten für Gerichte und Getränke
# ========================================
DISHES = [
    ("Pizza", 8.5),
    ("Pasta", 7.0),
    ("Salat", 5.5),
    ("Schnitzel", 9.0),
    ("Burger", 8.0),
    ("Risotto", 10.0),
    ("Suppe", 6.0)
]
DRINKS = [
    ("Wasser", 2.0),
    ("Cola", 2.5),
    ("Bier", 3.0),
    ("Wein", 4.0)
]

def get_next_7_days():
    today = datetime.now().date()
    return [(today + timedelta(days=i)).strftime("%d.%m.%Y") for i in range(7)]

def get_time_slots():
    return [f"{h}:00 - {h+2}:00" for h in range(16, 22, 2)]

# ========================================
# Klassen Table, Reservation, ReservationManager
# ========================================
class Table:
    def __init__(self, number, seats):
        self.number = number
        self.seats = seats
        self.orders = {"dishes": [0]*len(DISHES), "drinks": [0]*len(DRINKS)}
        ### NEU: Zustände für die Kommunikation mit dem Pico
        self.is_service_requested = False
        self.is_bill_requested = False
        self.service_counter = 0
        self.bill_counter = 0
        self.is_seen_by_staff = False
        # Die GUI-interne "belegt" und "reserviert" Logik bleibt
        # wird aber durch Pico-Status überschrieben, wenn verbunden
        self.is_occupied_gui = False
        self.is_reserved_gui = False

    def reset_orders(self):
        self.orders = {"dishes": [0]*len(DISHES), "drinks": [0]*len(DRINKS)}

    def total(self):
        total = sum(q * price for q, (_, price) in zip(self.orders["dishes"], DISHES))
        total += sum(q * price for q, (_, price) in zip(self.orders["drinks"], DRINKS))
        return total

class Reservation:
    def __init__(self, name, table_number, date, time_slot):
        self.name = name
        self.table_number = table_number
        self.date = date
        self.time_slot = time_slot
    def __lt__(self, other):
        dt1 = datetime.strptime(f"{self.date} {self.time_slot[:2]}", "%d.%m.%Y %H")
        dt2 = datetime.strptime(f"{other.date} {other.time_slot[:2]}", "%d.%m.%Y %H")
        return dt1 < dt2

class ReservationManager:
    def __init__(self):
        self.reservations = []
    def add_reservation(self, r):
        self.reservations.append(r)
        self.reservations.sort()
    def remove_reservation(self, table_number, date, time_slot):
        self.reservations = [
            r for r in self.reservations
            if not (r.table_number == table_number and r.date == date and r.time_slot == time_slot)
        ]
    def is_reserved(self, table_number, date, time_slot):
        return any(
            r.table_number == table_number and r.date == date and r.time_slot == time_slot
            for r in self.reservations
        )
    def get_reservations(self):
        return sorted(self.reservations)

# ========================================
# Beispielgraph für Servicewege
# ========================================
SERVICE_GRAPH = ds.Graph()
SERVICE_GRAPH.add_edge(1, 2, 1.2)
SERVICE_GRAPH.add_edge(2, 3, 1.5)
SERVICE_GRAPH.add_edge(3, 4, 2.0)

# ========================================
# Hauptklasse mit GUI
# ========================================
class RestaurantGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Restaurant Verwaltung")
        self.tables = [Table(i, seats) for i, seats in enumerate([2, 4, 6, 8], 1)]
        self.res_manager = ReservationManager()
        self.selected_table = None

        ### NEU: Serielle Kommunikation Variablen
        self.ser = None
        self.pico_connected = False
        self.running_serial_threads = False
        self.pico_data_queue = queue.Queue()
        self.gui_command_queue = queue.Queue()

        self.build_ui()
        self.update_table_status() # Initialer Aufruf
        self.connect_to_pico() # Versuch, beim Start zu verbinden
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing) # Handler für Fenster schließen
        self.check_pico_queue() # Starte den regelmäßigen Check

    ### NEU: Methoden für serielle Kommunikation
    def find_pico_port(self):
        ports = serial.tools.list_ports.comports()
        for p in ports:
            # Häufige PIDs/VIDs für Raspberry Pi Pico (CircuitPython/MicroPython CDC)
            if (p.vid == 0x2E8A and (p.pid == 0x0005 or p.pid == 0x000A)) or "USB Serial Device" in p.description or "ttyACM" in p.device:
                print(f"Möglicher Pico Port gefunden: {p.device}")
                return p.device
        print("Kein Pico Port gefunden.")
        return None

    def serial_reader_thread(self):
        while self.running_serial_threads:
            if self.ser and self.ser.is_open:
                try:
                    line = self.ser.readline().decode('utf-8').strip()
                    if line:
                        print(f"[GUI-Serial-Thread] Empfangen: {line}")
                        self.pico_data_queue.put(line)
                except serial.SerialException as e:
                    print(f"[GUI-Serial-Thread] Fehler beim Lesen vom Pico: {e}")
                    self.pico_connected = False
                    self.running_serial_threads = False
                    self.ser = None
                    break
                except Exception as e:
                    print(f"[GUI-Serial-Thread] Unerwarteter Fehler im Reader: {e}")
                    self.pico_connected = False
                    self.running_serial_threads = False
                    self.ser = None
                    break
            time.sleep(0.01)

    def serial_writer_thread(self):
        while self.running_serial_threads:
            if self.ser and self.ser.is_open:
                if not self.gui_command_queue.empty():
                    command = self.gui_command_queue.get()
                    try:
                        self.ser.write((command + '\n').encode('utf-8'))
                        print(f"[GUI-Serial-Thread] Gesendet: {command}")
                    except serial.SerialException as e:
                        print(f"[GUI-Serial-Thread] Fehler beim Senden von Daten: {e}")
                        self.pico_connected = False
                        self.running_serial_threads = False
                        self.ser = None
                        break
                    except Exception as e:
                        print(f"[GUI-Serial-Thread] Unerwarteter Fehler im Writer: {e}")
                        self.pico_connected = False
                        self.running_serial_threads = False
                        self.ser = None
                        break
            time.sleep(0.01)

    def connect_to_pico(self):
        if self.pico_connected:
            return True

        port = self.find_pico_port()
        if port:
            try:
                self.ser = serial.Serial(port, 115200, timeout=1)
                self.pico_connected = True
                self.running_serial_threads = True
                threading.Thread(target=self.serial_reader_thread, daemon=True).start()
                threading.Thread(target=self.serial_writer_thread, daemon=True).start()
                print("GUI: Verbindung zum Pico hergestellt.")
                return True
            except serial.SerialException as e:
                print(f"GUI: Fehler beim Verbinden mit Pico: {e}")
                messagebox.showerror("Verbindungsfehler", f"Konnte keine Verbindung zum Pico herstellen: {e}")
                self.pico_connected = False
                self.running_serial_threads = False
                self.ser = None
                return False
        else:
            messagebox.showwarning("Pico nicht gefunden", "Der Raspberry Pi Pico wurde nicht gefunden. Bitte prüfen Sie die Verbindung.")
            self.pico_connected = False
            self.running_serial_threads = False
            self.ser = None
            return False

    def disconnect_pico(self):
        if self.pico_connected:
            self.running_serial_threads = False # Signal zum Beenden der Threads
            if self.ser and self.ser.is_open:
                self.ser.close()
                print("GUI: Verbindung zum Pico getrennt.")
            self.pico_connected = False
            self.ser = None

    def send_command_to_pico(self, command):
        if self.pico_connected:
            self.gui_command_queue.put(command)
        else:
            print(f"GUI: Nicht mit Pico verbunden, Befehl '{command}' nicht gesendet.")
            # Optional: Hier einen Hinweis in der GUI anzeigen

    def check_pico_queue(self):
        """Wird regelmäßig vom Tkinter-Hauptloop aufgerufen."""
        while not self.pico_data_queue.empty():
            response_line = self.pico_data_queue.get()
            self.process_pico_response(response_line)
        self.root.after(100, self.check_pico_queue) # Nächsten Check planen

    def process_pico_response(self, response_line):
        """Verarbeitet eine einzelne Zeile, die vom Pico empfangen wurde."""
        parts = response_line.split(':')
        if len(parts) >= 3 and parts[0] == "STATUS":
            key = parts[1]
            value_str = parts[2]
            table_idx = 0 # Da dein Pico-Code für EINEN Tisch ist, nehmen wir Tisch 1 (Index 0)

            # Konvertiere String-Werte in die richtigen Python-Typen
            actual_value = None
            if value_str == "TRUE":
                actual_value = True
            elif value_str == "FALSE":
                actual_value = False
            else:
                try:
                    actual_value = int(value_str)
                except ValueError:
                    try:
                        actual_value = float(value_str)
                    except ValueError:
                        actual_value = value_str # Behandle als String

            # Aktualisiere den internen Zustand des Table-Objekts basierend auf dem Schlüssel
            if key == "SERVICE_ERWUENSCHT":
                self.tables[table_idx].is_service_requested = actual_value
            elif key == "RECHNUNG_ERWUENSCHT":
                self.tables[table_idx].is_bill_requested = actual_value
            elif key == "SERVICE_ZAEHLER":
                self.tables[table_idx].service_counter = actual_value
            elif key == "RECHNUNG_ZAEHLER":
                self.tables[table_idx].bill_counter = actual_value
            elif key == "TISCH_GESEHEN":
                self.tables[table_idx].is_seen_by_staff = actual_value
            elif key == "TISCH_RESERVIERT":
                # Diese Variable steuert die LED auf dem Pico
                # Für die GUI nutzen wir weiterhin die eigene Reservierungslogik,
                # aber wir können sie hier ggf. synchronisieren oder anzeigen
                self.tables[table_idx].is_reserved_gui = actual_value
            elif key == "TISCH_BELEGT":
                # Diese Variable steuert die LED auf dem Pico
                # Für die GUI nutzen wir weiterhin die eigene Belegt-Logik (Bestellfenster)
                # aber wir können sie hier ggf. synchronisieren oder anzeigen
                self.tables[table_idx].is_occupied_gui = actual_value
            elif key == "TISCH_SERVICE_ERLEDIGT":
                # Diese Variable wird vom Pico zurückgesetzt, wenn ein Wunsch da ist
                # Entspricht der SET SERVICE_DONE ON/OFF vom GUI-Befehl
                # Im Pico-Code wird diese Variable auch auf False gesetzt, wenn ein Wunsch da ist
                pass # Diese Variable wird primär vom GUI zum Pico gesendet
            elif key == "TISCH_RECHNUNG_ERLEDIGT":
                pass # Diese Variable wird primär vom GUI zum Pico gesendet
            else:
                print(f"GUI: Unbekannter Status-Key vom Pico: {key}")

            self.update_table_status_display(self.tables[table_idx]) # Aktualisiere nur den einen Tisch
            self.update_additional_status_display() # Update für Service/Rechnungstasten-Status

        elif len(parts) >= 2 and parts[0] == "BUTTON":
            button_type = parts[1]
            table_idx = 0 # Da dein Pico-Code für EINEN Tisch ist

            if button_type == "SERVICE_PRESSED":
                messagebox.showinfo("Pico-Info", "Service-Taster wurde gedrückt!")
                # Der service_counter und is_service_requested werden bereits über STATUS aktualisiert
            elif button_type == "RECHNUNG_PRESSED":
                messagebox.showinfo("Pico-Info", "Rechnungs-Taster wurde gedrückt!")
                # Der bill_counter und is_bill_requested werden bereits über STATUS aktualisiert
            self.update_table_status_display(self.tables[table_idx])
            self.update_additional_status_display()
        else:
            print(f"GUI: Unbekanntes oder fehlerhaftes Protokoll vom Pico: {response_line}")

    def on_closing(self):
        """Wird aufgerufen, wenn das GUI-Fenster geschlossen wird."""
        self.disconnect_pico()
        self.root.destroy()

    def build_ui(self):
        # ... (Dein existierender GUI-Aufbau bleibt größtenteils gleich) ...
        # — Tische-Frame —
        self.tables_frame = tk.Frame(self.root)
        self.tables_frame.grid(row=0, column=0, padx=10, pady=10, sticky="n")
        self.table_buttons = []
        for i, table in enumerate(self.tables):
            btn = tk.Button(
                self.tables_frame,
                text=f"Tisch {table.number}\n({table.seats} Plätze)",
                width=15, height=4,
                command=lambda t=table: self.open_order_window(t)
            )
            btn.grid(row=i, column=0, pady=5)
            self.table_buttons.append(btn)

        # — Reservierungsbereich —
        self.res_frame = ttk.LabelFrame(self.root, text="Reservierung", padding=10)
        self.res_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        ttk.Label(self.res_frame, text="Name:").grid(row=0, column=0)
        self.name_entry = ttk.Entry(self.res_frame); self.name_entry.grid(row=0,column=1)
        ttk.Label(self.res_frame, text="Tisch:").grid(row=1, column=0)
        self.table_choice = ttk.Combobox(self.res_frame, values=[t.number for t in self.tables], width=3)
        self.table_choice.grid(row=1,column=1)
        ttk.Label(self.res_frame, text="Tag:").grid(row=2, column=0)
        self.day_choice = ttk.Combobox(self.res_frame, values=get_next_7_days(), width=12)
        self.day_choice.grid(row=2,column=1)
        ttk.Label(self.res_frame, text="Zeit:").grid(row=3, column=0)
        self.time_choice = ttk.Combobox(self.res_frame, values=get_time_slots(), width=12)
        self.time_choice.grid(row=3,column=1)
        ttk.Button(self.res_frame, text="Reservieren", command=self.reserve_table).grid(row=4, column=0, pady=5)
        ttk.Button(self.res_frame, text="Stornieren", command=self.cancel_reservation).grid(row=4, column=1, pady=5)
        self.res_listbox = tk.Listbox(self.res_frame, width=40)
        self.res_listbox.grid(row=5, column=0, columnspan=2, pady=5)

        ### NEU: Pico-Steuerung und Status-Anzeige
        self.pico_control_frame = ttk.LabelFrame(self.root, text="Tischstatus & Pico-Steuerung (Tisch 1)", padding=10)
        self.pico_control_frame.grid(row=0, column=2, padx=10, pady=10, sticky="n")

        # Statusanzeigen
        ttk.Label(self.pico_control_frame, text="Service Status:").grid(row=0, column=0, sticky="w")
        self.lbl_service_status = ttk.Label(self.pico_control_frame, text="N/A", foreground="grey")
        self.lbl_service_status.grid(row=0, column=1, sticky="w")

        ttk.Label(self.pico_control_frame, text="Rechnung Status:").grid(row=1, column=0, sticky="w")
        self.lbl_rechnung_status = ttk.Label(self.pico_control_frame, text="N/A", foreground="grey")
        self.lbl_rechnung_status.grid(row=1, column=1, sticky="w")

        ttk.Label(self.pico_control_frame, text="Gesehen Status:").grid(row=2, column=0, sticky="w")
        self.lbl_gesehen_status = ttk.Label(self.pico_control_frame, text="N/A", foreground="grey")
        self.lbl_gesehen_status.grid(row=2, column=1, sticky="w")

        ttk.Label(self.pico_control_frame, text="Service Zähler:").grid(row=3, column=0, sticky="w")
        self.lbl_service_counter = ttk.Label(self.pico_control_frame, text="0")
        self.lbl_service_counter.grid(row=3, column=1, sticky="w")

        ttk.Label(self.pico_control_frame, text="Rechnung Zähler:").grid(row=4, column=0, sticky="w")
        self.lbl_rechnung_counter = ttk.Label(self.pico_control_frame, text="0")
        self.lbl_rechnung_counter.grid(row=4, column=1, sticky="w")


        # Steuerungstasten
        ttk.Button(self.pico_control_frame, text="Service Erledigt", command=lambda: self.send_command_to_pico("SET SERVICE_DONE ON")).grid(row=5, column=0, columnspan=2, pady=5)
        ttk.Button(self.pico_control_frame, text="Rechnung Erledigt", command=lambda: self.send_command_to_pico("SET RECHNUNG_DONE ON")).grid(row=6, column=0, columnspan=2, pady=5)
        ttk.Button(self.pico_control_frame, text="Als Gesehen Markieren", command=lambda: self.send_command_to_pico("SET GESEHEN ON")).grid(row=7, column=0, columnspan=2, pady=5)
        ttk.Separator(self.pico_control_frame, orient="horizontal").grid(row=8, column=0, columnspan=2, sticky="ew", pady=5)

        # Tisch-Status von GUI an Pico senden (Belegt/Reserviert)
        ttk.Label(self.pico_control_frame, text="GUI Tischstatus an Pico:").grid(row=9, column=0, columnspan=2, sticky="w")
        ttk.Button(self.pico_control_frame, text="Tisch 1 Belegt (Pico)", command=lambda: self.send_command_to_pico("SET BELEGT ON")).grid(row=10, column=0, pady=2, sticky="ew")
        ttk.Button(self.pico_control_frame, text="Tisch 1 Frei (Pico)", command=lambda: self.send_command_to_pico("SET BELEGT OFF")).grid(row=10, column=1, pady=2, sticky="ew")
        ttk.Button(self.pico_control_frame, text="Tisch 1 Reserviert (Pico)", command=lambda: self.send_command_to_pico("SET RESERVIERT ON")).grid(row=11, column=0, pady=2, sticky="ew")
        ttk.Button(self.pico_control_frame, text="Tisch 1 Reservierung aufheben (Pico)", command=lambda: self.send_command_to_pico("SET RESERVIERT OFF")).grid(row=11, column=1, pady=2, sticky="ew")


        # — DS & Algos —
        self.panel_ds = ttk.LabelFrame(self.root, text="Data Structures & Algos", padding=10)
        self.panel_ds.grid(row=1, column=0, columnspan=2, padx=10, pady=10, sticky="ew")
        ttk.Button(self.panel_ds, text="Sortiere Tische nach Umsatz", command=self.run_sort_test).grid(row=0, column=0, padx=5, pady=2)
        ttk.Button(self.panel_ds, text="Optimaler Servicepfad", command=self.shortest_path).grid(row=0, column=1, padx=5, pady=2)

        # — Suchfunktion für Gerichte —
        self.search_frame = ttk.LabelFrame(self.root, text="Gericht suchen", padding=10)
        self.search_frame.grid(row=2, column=0, columnspan=2, padx=10, pady=10, sticky="ew")
        ttk.Label(self.search_frame, text="Suchbegriff:").grid(row=0, column=0)
        self.search_entry = ttk.Entry(self.search_frame)
        self.search_entry.grid(row=0, column=1)
        ttk.Button(self.search_frame, text="Suchen", command=self.search_dishes).grid(row=0, column=2, padx=5)
        self.search_results = tk.Listbox(self.search_frame, width=40, height=5)
        self.search_results.grid(row=1, column=0, columnspan=3, pady=5)
        self.search_results.bind("<<ListboxSelect>>", self.on_select_dish)

    # ========================================
    # Methoden zur Suchfunktion (unverändert)
    # ========================================
    def search_dishes(self):
        term = self.search_entry.get().strip().lower()
        self.search_results.delete(0, tk.END)
        if not term:
            return
        matches = [f"{dish} – {price:.2f} €" for dish, price in DISHES if term in dish.lower()]
        if matches:
            for m in matches:
                self.search_results.insert(tk.END, m)
        else:
            self.search_results.insert(tk.END, "Keine Treffer gefunden.")

    def on_select_dish(self, event):
        sel = event.widget.curselection()
        if not sel:
            return
        text = event.widget.get(sel[0])
        if text == "Keine Treffer gefunden.":
            return
        dish = text.split(" – ")[0]
        price = next(p for d, p in DISHES if d == dish)
        messagebox.showinfo("Gericht gefunden", f"{dish}: {price:.2f} €")

    # ========================================
    # Rest der Methoden (angepasst für Pico-Status)
    # ========================================
    def update_table_status(self):
        """
        Aktualisiert den primären Tischstatus (Farbe/Text) basierend auf GUI-Reservierungen.
        Dies läuft unabhängig vom Pico-Status.
        """
        today = datetime.now().strftime("%d.%m.%Y")
        current_hour = datetime.now().hour
        for i, table in enumerate(self.tables):
            # Prüfe, ob Tisch nach GUI-Reservierungslogik aktuell belegt ist
            occupied_by_reservation = any(
                self.res_manager.is_reserved(table.number, today, slot)
                and int(slot[:2]) <= current_hour < int(slot[:2]) + 2
                for slot in get_time_slots()
            )
            # Update des Button-Status (Farbe und Text) basierend auf GUI-Zustand
            btn = self.table_buttons[i]
            if occupied_by_reservation:
                btn.config(bg="red")
                btn.config(text=f"Tisch {table.number}\nbelegt (GUI)")
            else:
                btn.config(bg="lightgreen")
                btn.config(text=f"Tisch {table.number}\n{table.seats} Plätze")
            # Update des speziellen Pico-Status-Anzeigebereichs für Tisch 1
            if table.number == 1:
                self.update_table_status_display(table)
                self.update_additional_status_display()

        # Plane den nächsten GUI-internen Status-Update
        self.root.after(1000, self.update_table_status) # Aktualisiert alle 1 Sekunde

    def update_table_status_display(self, table):
        """
        Aktualisiert die dedizierten Labels für Tisch 1 basierend auf Pico-Daten.
        """
        if table.number == 1: # Wir aktualisieren nur für Tisch 1, da der Pico nur einen Tisch steuert
            service_color = "red" if table.is_service_requested else "green"
            rechnung_color = "red" if table.is_bill_requested else "green"
            gesehen_color = "orange" if table.is_seen_by_staff else "green"

            self.lbl_service_status.config(text="JA" if table.is_service_requested else "NEIN", foreground=service_color)
            self.lbl_rechnung_status.config(text="JA" if table.is_bill_requested else "NEIN", foreground=rechnung_color)
            self.lbl_gesehen_status.config(text="JA" if table.is_seen_by_staff else "NEIN", foreground=gesehen_color)
            self.lbl_service_counter.config(text=str(table.service_counter))
            self.lbl_rechnung_counter.config(text=str(table.bill_counter))

    def update_additional_status_display(self):
        """
        Kann für weitere allgemeine Statusanzeigen verwendet werden,
        z.B. den Verbindungsstatus zum Pico.
        """
        # Beispiel: Status der Pico-Verbindung anzeigen
        # (Du könntest hier ein weiteres Label in der GUI hinzufügen)
        # self.lbl_pico_connection_status.config(text=f"Pico Verbunden: {'Ja' if self.pico_connected else 'Nein'}")
        pass # Im Moment nicht explizit für dieses Beispiel benötigt

    def open_order_window(self, table):
        if self.is_table_reserved_now(table.number):
            messagebox.showinfo("Tisch belegt", "Dieser Tisch ist aktuell reserviert!")
            return
        self.selected_table = table
        win = tk.Toplevel(self.root)
        win.title(f"Bestellung für Tisch {table.number}")
        dish_vars, drink_vars = [], []

        for i, (dish, price) in enumerate(DISHES):
            ttk.Label(win, text=f"{dish} ({price:.2f}€):").grid(row=i, column=0, sticky="w")
            var = tk.IntVar(value=table.orders["dishes"][i])
            dish_vars.append(var)
            ttk.Entry(win, textvariable=var, width=4).grid(row=i, column=1)

        for i, (drink, price) in enumerate(DRINKS):
            ttk.Label(win, text=f"{drink} ({price:.2f}€):").grid(row=i, column=2, sticky="w")
            var = tk.IntVar(value=table.orders["drinks"][i])
            drink_vars.append(var)
            ttk.Entry(win, textvariable=var, width=4).grid(row=i, column=3)

        def save_order():
            table.orders["dishes"] = [v.get() for v in dish_vars]
            table.orders["drinks"] = [v.get() for v in drink_vars]
            messagebox.showinfo("Gespeichert", "Bestellung gespeichert.")

        def show_bill():
            save_order()
            total = table.total()
            messagebox.showinfo("Rechnung", f"Gesamtsumme: {total:.2f} €")
            table.reset_orders()
            win.destroy()

        ttk.Button(win, text="Speichern", command=save_order).grid(row=len(DISHES)+1, column=0, pady=5)
        ttk.Button(win, text="Rechnung", command=show_bill).grid(row=len(DISHES)+1, column=1, pady=5)

    def is_table_reserved_now(self, table_number):
        today = datetime.now().strftime("%d.%m.%Y")
        current_hour = datetime.now().hour
        return any(
            self.res_manager.is_reserved(table_number, today, slot)
            and int(slot[:2]) <= current_hour < int(slot[:2]) + 2
            for slot in get_time_slots()
        )

    def reserve_table(self):
        name = self.name_entry.get().strip()
        try:
            table_number = int(self.table_choice.get())
        except ValueError:
            messagebox.showerror("Fehler", "Bitte gültigen Tisch wählen.")
            return
        date = self.day_choice.get().strip()
        slot = self.time_choice.get().strip()
        if not (name and date and slot):
            messagebox.showerror("Fehler", "Alle Felder ausfüllen.")
            return
        if self.res_manager.is_reserved(table_number, date, slot):
            messagebox.showerror("Fehler", "Bereits reserviert.")
            return
        self.res_manager.add_reservation(Reservation(name, table_number, date, slot))
        self.refresh_res()
        messagebox.showinfo("Reserviert", "Erfolgreich.")
        # Sende Reservierungsstatus an Pico, falls es Tisch 1 ist
        if table_number == 1:
            # Wichtig: "RESERVIERT ON" auf Pico setzt nur die Anzeige auf dem Pico,
            # die GUI behält ihre eigene interne Reservierungslogik
            self.send_command_to_pico("SET RESERVIERT ON")
            # Falls Tisch 1 auch belegt wird durch die Reservierung (jetzt), sende auch BELEGT ON
            if self.is_table_reserved_now(1):
                self.send_command_to_pico("SET BELEGT ON")


    def cancel_reservation(self):
        try:
            table_number = int(self.table_choice.get())
        except ValueError:
            messagebox.showerror("Fehler", "Bitte gültigen Tisch wählen.")
            return
        date = self.day_choice.get().strip()
        slot = self.time_choice.get().strip()
        self.res_manager.remove_reservation(table_number, date, slot)
        self.refresh_res()
        messagebox.showinfo("Storniert", "Reservierung storniert.")
        # Sende Stornierungsstatus an Pico, falls es Tisch 1 ist
        if table_number == 1:
            self.send_command_to_pico("SET RESERVIERT OFF")
            # Falls Tisch 1 durch Stornierung nun frei wird
            if not self.is_table_reserved_now(1):
                self.send_command_to_pico("SET BELEGT OFF")

    def refresh_res(self):
        self.update_table_status() # Updated die Haupt-Tischbuttons
        self.res_listbox.delete(0, tk.END)
        for r in self.res_manager.get_reservations():
            self.res_listbox.insert(tk.END, f"{r.date} {r.time_slot} – Tisch {r.table_number} ({r.name})")

    def run_sort_test(self):
        orders = [t.total() for t in self.tables]
        sorted_orders, dur = ds.measure(ds.merge_sort, orders)
        messagebox.showinfo("Sortierung",
                             f"Totals: {orders}\nSortiert: {sorted_orders}\nDauer: {dur*1000:.2f} ms")

    def shortest_path(self):
        d = ds.shortest_path(SERVICE_GRAPH, src=1)
        txt = "\n".join(f"Tisch {k}: {v:.1f} m" for k, v in d.items())
        messagebox.showinfo("Servicewege ab Tisch 1", txt)

# ========================================
# Anwendung starten
# ========================================
if __name__ == "__main__":
    root = tk.Tk()
    app = RestaurantGUI(root)
    root.mainloop()