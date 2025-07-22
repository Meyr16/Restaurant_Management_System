from machine import Pin, PWM
import time
import json
import sys
import select

TISCH_xxx_SERVIVE_ERLEDIGT = False
TISCH_xxx_RECHNUNG_ERLEDIGT = False
TISCH_xxx_GESEHEN = False
TISCH_xxx_RESERVIERT = False
TISCH_xxx_BELEGT = False

SERVICE_ERWÜNSCHT = False
RECHNUNG_ERWÜNSCHT = False

PIN_SERVICE_BUTTON = 19
PIN_RECHNUNG_BUTTON = 16
PIN_LED_R = 11
PIN_LED_G = 3
PIN_LED_B = 7

button_service = Pin(PIN_SERVICE_BUTTON, Pin.IN, Pin.PULL_DOWN)
button_rechnung = Pin(PIN_RECHNUNG_BUTTON, Pin.IN, Pin.PULL_DOWN)

DEBOUNCE_TIME = 0.2

service_erwuenscht_zaehler = 0
rechnung_erwuenscht_zaehler = 0
MAX_DRINGLICHKEIT_ZAEHLER = 10

last_service_press_time = 0
last_rechnung_press_time = 0

blink_state = False
last_blink_toggle_time = 0
BLINK_INTERVAL = 0.5

class RGBLED:
    COLORS = {
        "OFF":      (0,   0,   0),
        "RED":      (255, 0,   0),
        "GREEN":    (0,   255, 0),
        "BLUE":     (0,   0,   255),
        "YELLOW":   (255, 255, 0),
        "CYAN":     (0,   255, 255),
        "MAGENTA":  (255, 0,   255),
        "WHITE":    (255, 255, 255),
        "PURPLE":   (128, 0,   128),
        "LIGHT_BLUE": (128, 128, 255),
    }

    def __init__(self, pin_r, pin_g, pin_b, pwm_freq=5000, common_anode=False):
        self.common_anode = common_anode
        self.pwm_freq = pwm_freq
        self.pwm_r = PWM(Pin(pin_r))
        self.pwm_g = PWM(Pin(pin_g))
        self.pwm_b = PWM(Pin(pin_b))
        self.pwm_r.freq(self.pwm_freq)
        self.pwm_g.freq(self.pwm_freq)
        self.pwm_b.freq(self.pwm_freq)
        self.set_color_rgb(0, 0, 0)

    def _map_value(self, value):
        pwm_val = int(value * 65535 / 255)
        return 65535 - pwm_val if self.common_anode else pwm_val

    def set_color_rgb(self, r, g, b):
        self.pwm_r.duty_u16(self._map_value(r))
        self.pwm_g.duty_u16(self._map_value(g))
        self.pwm_b.duty_u16(self._map_value(b))

    def set_color_by_name(self, color_name):
        color_name = color_name.upper()
        if color_name in self.COLORS:
            r, g, b = self.COLORS[color_name]
            self.set_color_rgb(r, g, b)
        else:
            print("Fehler: Farbe '{}' nicht definiert.".format(color_name))

    def set_dringlichkeits_orange(self, dringlichkeit_factor):
        green_component = int(125 * (1.0 - dringlichkeit_factor))
        self.set_color_rgb(255, green_component, 0)

    def turn_off(self):
        self.set_color_rgb(0, 0, 0)

my_rgb_led = RGBLED(pin_r=PIN_LED_R, pin_g=PIN_LED_G, pin_b=PIN_LED_B, common_anode=False)
my_rgb_led.set_color_by_name("OFF")

def send_status():
    status = {
        "SERVICE_ERWUENSCHT": SERVICE_ERWÜNSCHT,
        "RECHNUNG_ERWUENSCHT": RECHNUNG_ERWÜNSCHT,
        "RESERVIERT": TISCH_xxx_RESERVIERT,
        "BELEGT": TISCH_xxx_BELEGT,
        "SERVICE_ERLEDIGT": TISCH_xxx_SERVIVE_ERLEDIGT,
        "RECHNUNG_ERLEDIGT": TISCH_xxx_RECHNUNG_ERLEDIGT,
        "GESEHEN": TISCH_xxx_GESEHEN,
        "SERVICE_ZAEHLER": service_erwuenscht_zaehler,
        "RECHNUNG_ZAEHLER": rechnung_erwuenscht_zaehler
    }
    print("STATUS:" + json.dumps(status))

def process_serial_commands():
    global TISCH_xxx_RESERVIERT, TISCH_xxx_BELEGT, \
           TISCH_xxx_SERVIVE_ERLEDIGT, TISCH_xxx_RECHNUNG_ERLEDIGT, \
           SERVICE_ERWÜNSCHT, RECHNUNG_ERWÜNSCHT, \
           rechnung_erwuenscht_zaehler, service_erwuenscht_zaehler, \
           TISCH_xxx_GESEHEN

    # Non-blocking read from stdin
    if select.select([sys.stdin], [], [], 0)[0]:
        try:
            command = sys.stdin.readline().strip().upper()
            if command.startswith("SET "):
                parts = command.split(' ')
                if len(parts) == 3:
                    variable_name = parts[1]
                    value_str = parts[2]
                    new_value = True if value_str == "ON" else (False if value_str == "OFF" else None)
                    if new_value is not None:
                        if variable_name == "RESERVIERT":
                            TISCH_xxx_RESERVIERT = new_value
                        elif variable_name == "BELEGT":
                            TISCH_xxx_BELEGT = new_value
                        elif variable_name == "SERVICE_DONE":
                            TISCH_xxx_SERVIVE_ERLEDIGT = new_value
                            if new_value:
                                SERVICE_ERWÜNSCHT = False
                                service_erwuenscht_zaehler = 0
                                TISCH_xxx_GESEHEN = False
                        elif variable_name == "RECHNUNG_DONE":
                            TISCH_xxx_RECHNUNG_ERLEDIGT = new_value
                            if new_value:
                                RECHNUNG_ERWÜNSCHT = False
                                rechnung_erwuenscht_zaehler = 0
                                TISCH_xxx_GESEHEN = False
                        elif variable_name == "GESEHEN":
                            TISCH_xxx_GESEHEN = new_value
                    else:
                        try:
                            num_value = int(value_str)
                            if variable_name == "SERVICE_ZAEHLER":
                                service_erwuenscht_zaehler = max(0, num_value)
                                SERVICE_ERWÜNSCHT = service_erwuenscht_zaehler > 0
                            elif variable_name == "RECHNUNG_ZAEHLER":
                                rechnung_erwuenscht_zaehler = max(0, num_value)
                                RECHNUNG_ERWÜNSCHT = rechnung_erwuenscht_zaehler > 0
                        except ValueError:
                            pass
        except Exception as e:
            print("Serial command error:", e)
            sys.stdout.flush()

while True:
    current_time = time.time()
    process_serial_commands()

    if button_service.value() == 1:
        if (current_time - last_service_press_time) > DEBOUNCE_TIME:
            service_erwuenscht_zaehler += 1
            SERVICE_ERWÜNSCHT = True
            TISCH_xxx_GESEHEN = False
            last_service_press_time = current_time

    if button_rechnung.value() == 1:
        if (current_time - last_rechnung_press_time) > DEBOUNCE_TIME:
            rechnung_erwuenscht_zaehler += 1
            RECHNUNG_ERWÜNSCHT = True
            TISCH_xxx_GESEHEN = False
            last_rechnung_press_time = current_time

    if service_erwuenscht_zaehler == 0:
        SERVICE_ERWÜNSCHT = False
    if rechnung_erwuenscht_zaehler == 0:
        RECHNUNG_ERWÜNSCHT = False

    dringlichkeit_zaehler = max(service_erwuenscht_zaehler, rechnung_erwuenscht_zaehler)
    dringlichkeit_factor = min(1.0, dringlichkeit_zaehler / MAX_DRINGLICHKEIT_ZAEHLER)

    if (SERVICE_ERWÜNSCHT or RECHNUNG_ERWÜNSCHT) and TISCH_xxx_GESEHEN:
        if (current_time - last_blink_toggle_time) > BLINK_INTERVAL:
            blink_state = not blink_state
            last_blink_toggle_time = current_time
        if blink_state:
            my_rgb_led.set_dringlichkeits_orange(dringlichkeit_factor)
        else:
            my_rgb_led.turn_off()
    elif SERVICE_ERWÜNSCHT or RECHNUNG_ERWÜNSCHT:
        my_rgb_led.set_dringlichkeits_orange(dringlichkeit_factor)
        TISCH_xxx_SERVIVE_ERLEDIGT = False
        TISCH_xxx_RECHNUNG_ERLEDIGT = False
    elif TISCH_xxx_RESERVIERT and not TISCH_xxx_BELEGT:
        my_rgb_led.set_color_by_name("RED")
        TISCH_xxx_GESEHEN = False
        TISCH_xxx_SERVIVE_ERLEDIGT = False
        TISCH_xxx_RECHNUNG_ERLEDIGT = False
    elif TISCH_xxx_BELEGT:
        my_rgb_led.set_color_by_name("GREEN")
        TISCH_xxx_GESEHEN = False
        TISCH_xxx_SERVIVE_ERLEDIGT = False
        TISCH_xxx_RECHNUNG_ERLEDIGT = False
    else:
        my_rgb_led.set_color_by_name("BLUE")
        TISCH_xxx_GESEHEN = False
        TISCH_xxx_SERVIVE_ERLEDIGT = False
        TISCH_xxx_RECHNUNG_ERLEDIGT = False

    send_status()
    time.sleep(0.5)