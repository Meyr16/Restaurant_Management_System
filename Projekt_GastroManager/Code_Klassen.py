import tkinter as tk
from tkinter import messagebox, ttk
from datetime import datetime, timedelta
import threading
import serial
import time
import ds  

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
SERVICE_GRAPH.add_edge(3, 4, 2.0)<  y<

        # Serielle Schnittstelle öffnen (Port ggf. anpassen!)
        try:
            self.serial_port = serial.Serial("COM8", 9600, timeout=1)  # Passe COM3 auf deinen Port an!
            threading.Thread(target=self.listen_serial, daemon=True).start()
        except Exception as e:
            messagebox.showerror("Fehler", f"Serielle Verbindung fehlgeschlagen:\n{e}")

    def build_ui(self):
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

        # — Statusanzeige für Service & Rechnung —
        self.status_frame = ttk.LabelFrame(self.root, text="Live-Status", padding=10)
        self.status_frame.grid(row=3, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

        self.service_status_var = tk.StringVar(value="Servicewunsch: unbekannt")
        self.rechnung_status_var = tk.StringVar(value="Rechnungswunsch: unbekannt")

        ttk.Label(self.status_frame, textvariable=self.service_status_var).grid(row=0, column=0, sticky="w", padx=5)
        ttk.Label(self.status_frame, textvariable=self.rechnung_status_var).grid(row=1, column=0, sticky="w", padx=5)

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

    def listen_serial(self):
        while True:
            try:
                if self.serial_port.in_waiting:
                    line = self.serial_port.readline().decode("utf-8").strip()
                    if line.startswith("STATUS SERVICE"):
                        status = "aktiv" if "ON" in line else "inaktiv"
                        self.service_status_var.set(f"Servicewunsch: {status}")
                    elif line.startswith("STATUS RECHNUNG"):
                        status = "aktiv" if "ON" in line else "inaktiv"
                        self.rechnung_status_var.set(f"Rechnungswunsch: {status}")
            except Exception as e:
                print(f"Serieller Fehler: {e}")
            time.sleep(0.1)

# ========================================
# Anwendung starten
# ========================================
if __name__ == "__main__":
    root = tk.Tk()
    app = RestaurantGUI(root)
    root.mainloop()