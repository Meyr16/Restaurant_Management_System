#klassen

class Tisch:
    def __init__(self, tisch_nr, sitzplaetze):
        self.tisch_id = tisch_nr
        self.sitzplaetze = sitzplaetze
        self.reservierungen = []  # Liste von (startzeit, endzeit)

    def ist_verfuegbar(self, startzeit, dauer=timedelta(hours=2)):
        endzeit = startzeit + dauer
        for res_start, res_ende in self.reservierungen:
            if startzeit < res_ende and endzeit > res_start:
                return False
        return True
    def reservieren(self, startzeit, dauer=timedelta(hours=2)):
        if self.ist_verfuegbar(startzeit, dauer):
            self.reservierungen.append((startzeit, startzeit + dauer))
            return True
        return False

class Restaurant:
    def __init__(self):
        self.tische = []

    def tisch_hinzufuegen(self, kapazitaet):
        tisch_id = len(self.tische) + 1
        self.tische.append(Tisch(tisch_id, kapazitaet))

    def reservieren(self, personenanzahl, startzeit):
        passende_tische = sorted(
            [t for t in self.tische if t.kapazitaet >= personenanzahl],
            key=lambda t: t.kapazitaet
        )
        for tisch in passende_tische:
            if tisch.reservieren(startzeit):
                print(f"Reservierung erfolgreich! Tisch {tisch.tisch_id} für {personenanzahl} Personen um {startzeit.strftime('%H:%M')}")
                return tisch.tisch_id
        print("Leider kein Tisch verfügbar zur gewünschten Zeit.")
        return None