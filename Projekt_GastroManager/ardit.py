# main.py
import tkinter as tk
from tkinter import messagebox, ttk
from datetime import datetime, timedelta
import ds
import serial
import json

Port = "COM8"  # Passe ggf. an!
Baud = 9600

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
    return [f"{h}:00 - {h+2}:00" for h in range(12, 22, 2)]

# ========================================
# Klassen Table, Reservation, ReservationManager
# ========================================
class Table:
    def __init__(self, number, seats):
        self.number = number
        self.seats = seats
        self.orders = {"dishes": [0]*len(DISHES), "drinks": [0]*len(DRINKS)}
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

        self.build_ui()
        self.update_table_status()

        try:
            self.ser = serial.Serial(Port, Baud, timeout=1)
            print("Serielle Verbindung hergestellt.")
        except serial.SerialException as e:
            messagebox.showerror("Serial Error", f"Fehler beim Öffnen von {Port}:\n{e}")
            self.ser = None
        self.poll_serial_status()

    def build_ui(self):
        # — Tische-Frame —
        self.tables_frame = tk.Frame(self.root)
        self.tables_frame.grid(row=0, column=0, padx=10, pady=10, sticky="n")
        self.table_buttons = []
        self.occupied_vars = []  # NEU: Liste für Belegt-Status
        for i, table in enumerate(self.tables):
            btn = tk.Button(
                self.tables_frame,
                text=f"Tisch {table.number}\n({table.seats} Plätze)",
                width=15, height=4,
                command=lambda t=table: self.open_order_window(t)
            )
            btn.grid(row=i, column=0, pady=5)
            self.table_buttons.append(btn)

            # NEU: Belegt/Ungenutzt-Button für jeden Tisch
            occ_var = tk.BooleanVar()
            self.occupied_vars.append(occ_var)
            def make_occupied_cmd(tablenr, var=occ_var):
                def cmd():
                    if var.get():
                        self.send_serial_command("SET BELEGT ON")
                    else:
                        self.send_serial_command("SET BELEGT OFF")
                return cmd
            occ_btn = tk.Checkbutton(
                self.tables_frame,
                text="Belegt",
                variable=occ_var,
                command=make_occupied_cmd(table.number, occ_var)
            )
            occ_btn.grid(row=i, column=1, padx=5)

        # — Reservierungsbereich —
        self.res_frame = ttk.LabelFrame(self.root, text="Reservierung", padding=10)
        self.res_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        ttk.Label(self.res_frame, text="Name:").grid(row=0, column=0)
        self.name_entry = ttk.Entry(self.res_frame); self.name_entry.grid(row=0,column=1)
        ttk.Label(self.res_frame, text="Tisch:").grid(row=1, column=0)
        self.table_choice = ttk.Combobox(self.res_frame, values=[1,2,3,4], width=3)
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

        # Bedienung/Rechnung Feld Tisch 1
        self.status_frame = tk.LabelFrame(self.root, text="Tisch1 Status", padx=10, pady=10)
        self.status_frame.grid(row=0, column=2, padx=10, pady=10, sticky="n")
        self.service_var = tk.BooleanVar()
        self.bill_var = tk.BooleanVar()
        tk.Checkbutton(self.status_frame, text="Bedienung erwünscht", variable=self.service_var,
                       command=self.trigger_service).pack(anchor="w")
        tk.Checkbutton(self.status_frame, text="Rechnung erwünscht", variable=self.bill_var,
                       command=self.trigger_bill).pack(anchor="w")
        self.status_labels = {}
        status_keys = [
            "SERVICE_ERWUENSCHT", "RECHNUNG_ERWUENSCHT", "RESERVIERT", "BELEGT",
            "SERVICE_ERLEDIGT", "RECHNUNG_ERLEDIGT", "GESEHEN"
        ]
        for key in status_keys:
            lbl = tk.Label(self.status_frame, text=f"{key}: ?")
            lbl.pack(anchor="w")
            self.status_labels[key] = lbl

        # Fortschrittsbalken für Service- und Rechnung-Zähler
        tk.Label(self.status_frame, text="Service Dringlichkeit:").pack(anchor="w", pady=(10,0))
        self.service_progress = ttk.Progressbar(self.status_frame, orient="horizontal", length=150, mode="determinate", maximum=10)
        self.service_progress.pack(anchor="w", pady=(0,5))
        tk.Label(self.status_frame, text="Rechnung Dringlichkeit:").pack(anchor="w")
        self.bill_progress = ttk.Progressbar(self.status_frame, orient="horizontal", length=150, mode="determinate", maximum=10)
        self.bill_progress.pack(anchor="w", pady=(0,5))
        tk.Button(self.status_frame, text="Reset (alle Variablen)", command=self.reset_all).pack(anchor="w", pady=(10,0))

    # ========================================
    # Methoden zur Suchfunktion
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
    # Rest der Methoden (wie in zuvor)
    # ========================================
    def update_table_status(self):
        today = datetime.now().strftime("%d.%m.%Y")
        current_hour = datetime.now().hour
        for i, table in enumerate(self.tables):
            occupied = any(
                self.res_manager.is_reserved(table.number, today, slot)
                and int(slot[:2]) <= current_hour < int(slot[:2]) + 2
                for slot in get_time_slots()
            )
            btn = self.table_buttons[i]
            btn.config(bg="red" if occupied else "lightgreen")
            btn.config(text=f"Tisch {table.number}\n{'belegt' if occupied else f'{table.seats} Plätze'}")

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
        # Microcontroller informieren
        self.send_serial_command("SET RESERVIERT ON")
        messagebox.showinfo("Reserviert", "Erfolgreich.")

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
        # Microcontroller informieren
        self.send_serial_command("SET RESERVIERT OFF")
        messagebox.showinfo("Storniert", "Reservierung storniert.")

    def refresh_res(self):
        self.update_table_status()
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

    def trigger_service(self):
        if self.service_var.get():
            self.send_serial_command("SET SERVICE_ZAEHLER 1")
            self.popup_status("Bedienung erwünscht", "Bedienung für Tisch 1 gewünscht.", self.service_var)

    def trigger_bill(self):
        if self.bill_var.get():
            self.send_serial_command("SET RECHNUNG_ZAEHLER 1")
            self.popup_status("Rechnung erwünscht", "Rechnung für Tisch 1 gewünscht.", self.bill_var)

    def popup_status(self, title, msg, var):
        win = tk.Toplevel(self.root)
        win.title(title)
        tk.Label(win, text=msg).pack(padx=20, pady=10)
        def confirm():
            # Beim Bestätigen den passenden Zähler auf 0 setzen
            if "Bedienung" in title:
                self.send_serial_command("SET SERVICE_ZAEHLER 0")
            elif "Rechnung" in title:
                self.send_serial_command("SET RECHNUNG_ZAEHLER 0")
            var.set(False)
            win.destroy()
        tk.Button(win, text="Bestätigen", command=confirm).pack(pady=10)

    def send_serial_command(self, command):
        if self.ser and self.ser.is_open:
            try:
                self.ser.write((command + '\n').encode('utf-8'))
                print(f"[SERIAL OUT] {command}")
            except Exception as e:
                messagebox.showerror("Serial Error", f"Fehler beim Senden:\n{e}")
        else:
            print("Serielle Verbindung nicht geöffnet.")

    def poll_serial_status(self):
        if self.ser and self.ser.in_waiting:
            try:
                line = self.ser.readline().decode("utf-8").strip()
                if line.startswith("STATUS:"):
                    status = json.loads(line[7:])
                    # Zähler zurücksetzen, wenn erledigt
                    if status.get("SERVICE_ERLEDIGT"):
                        status["SERVICE_ZAEHLER"] = 0
                    if status.get("RECHNUNG_ERLEDIGT"):
                        status["RECHNUNG_ZAEHLER"] = 0
                    # Status-Labels aktualisieren
                    for key, lbl in self.status_labels.items():
                        val = status.get(key, "?")
                        lbl.config(text=f"{key}: {val}")
                    # Fortschrittsbalken aktualisieren
                    self.service_progress['value'] = status.get("SERVICE_ZAEHLER", 0)
                    self.bill_progress['value'] = status.get("RECHNUNG_ZAEHLER", 0)
            except Exception as e:
                print(f"Serial read error: {e}")
        self.root.after(500, self.poll_serial_status)

    def reset_all(self):
        cmds = [
            "SET SERVICE_ERWUENSCHT OFF",
            "SET RECHNUNG_ERWUENSCHT OFF",
            "SET RESERVIERT OFF",
            "SET BELEGT OFF",
            "SET SERVICE_ERLEDIGT OFF",
            "SET RECHNUNG_ERLEDIGT OFF",
            "SET GESEHEN OFF",
            "SET SERVICE_ZAEHLER 0",
            "SET RECHNUNG_ZAEHLER 0"
        ]
        for cmd in cmds:
            self.send_serial_command(cmd)
# ========================================
# Anwendung starten
# ========================================
if __name__ == "__main__":
    root = tk.Tk()
    app = RestaurantGUI(root)
    root.mainloop()