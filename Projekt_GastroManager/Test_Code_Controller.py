from machine import Pin
import time

# --- Konfiguration der GPIO-Pins ---
# Taster (Pull-Down Konfiguration: HIGH wenn gedrückt, LOW sonst)
# Pin 14 für "Service"
PIN_SERVICE_BUTTON = 14
# Pin 15 für "Rechnung"
PIN_RECHNUNG_BUTTON = 15

# RGB LED (gemeinsame Kathode: HIGH = AN, LOW = AUS)
# Passe diese Pins an, falls deine LED anders verdrahtet ist
PIN_LED_ROT   = 11
PIN_LED_GRUEN = 12
PIN_LED_BLAU  = 13

# Entprellzeit in Sekunden (für beide Taster)
DEBOUNCE_TIME = 0.2 # 200 Millisekunden

# --- Variablen zur Zählung ---
service_erwuenscht_zaehler = 0
rechnung_erwuenscht_zaehler = 0

# --- Pin-Initialisierung ---
# Taster-Pins als Eingang mit Pull-Down Widerstand
button_service = Pin(PIN_SERVICE_BUTTON, Pin.IN, Pin.PULL_DOWN)
button_rechnung = Pin(PIN_RECHNUNG_BUTTON, Pin.IN, Pin.PULL_DOWN)

# LED-Pins als Ausgang
led_rot   = Pin(PIN_LED_ROT, Pin.OUT)
led_gruen = Pin(PIN_LED_GRUEN, Pin.OUT)
led_blau  = Pin(PIN_LED_BLAU, Pin.OUT)

# --- Hilfsfunktion zum Steuern der RGB-LED ---
# True = LED leuchtet (HIGH), False = LED ist aus (LOW) bei gemeinsamer Kathode
def set_rgb(rot, gruen, blau):
    led_rot.value(rot)
    led_gruen.value(gruen)
    led_blau.value(blau)

# --- Initialisierung der LED-Farbe ---
# Startet mit Blau, um anzuzeigen, dass das System bereit ist
set_rgb(False, False, True) # Blau

print("Programm gestartet. Warte auf Tasterdruck...")
print(f"Service Zaehler: {service_erwuenscht_zaehler}, Rechnung Zaehler: {rechnung_erwuenscht_zaehler}")

# --- Hauptprogrammschleife ---
while True:
    # Flag, um festzuhalten, ob irgendein Taster gerade gedrückt wurde
    # Dies hilft, die LED-Farbe entsprechend zu setzen
    irgendein_taster_gedrueckt = False

    # Taster für "Service erwünscht" prüfen
    if button_service.value(): # .value() gibt True zurück, wenn der Taster gedrückt ist
        service_erwuenscht_zaehler += 1
        print(f"Service erwuenscht! Neuer Zaehlerstand: {service_erwuenscht_zaehler}")
        set_rgb(False, True, False) # LED auf Grün
        irgendein_taster_gedrueckt = True
        
        # Entprellen: Warte, bis der Taster losgelassen wird ODER die maximale Entprellzeit abgelaufen ist
        start_time = time.time()
        while button_service.value() and (time.time() - start_time) < DEBOUNCE_TIME:
            time.sleep(0.05) # Kleine Pause, um CPU zu entlasten
        # Zusätzliche Schleife, falls Taster länger gedrückt bleibt
        while button_service.value():
            time.sleep(0.05)


    # Taster für "Rechnung erwünscht" prüfen
    if button_rechnung.value(): # .value() gibt True zurück, wenn der Taster gedrückt ist
        rechnung_erwuenscht_zaehler += 1
        print(f"Rechnung erwuenscht! Neuer Zaehlerstand: {rechnung_erwuenscht_zaehler}")
        set_rgb(True, False, False) # LED auf Rot
        irgendein_taster_gedrueckt = True
        
        # Entprellen: Warte, bis der Taster losgelassen wird ODER die maximale Entprellzeit abgelaufen ist
        start_time = time.time()
        while button_rechnung.value() and (time.time() - start_time) < DEBOUNCE_TIME:
            time.sleep(0.05) # Kleine Pause, um CPU zu entlasten
        # Zusätzliche Schleife, falls Taster länger gedrückt bleibt
        while button_rechnung.value():
            time.sleep(0.05)

    # Wenn kein Taster aktiv gedrückt ist, geht die LED zurück auf Blau
    if not irgendein_taster_gedrueckt:
        set_rgb(False, False, True) # LED auf Blau

    time.sleep(0.05) # Kurze Pause in der Hauptschleife