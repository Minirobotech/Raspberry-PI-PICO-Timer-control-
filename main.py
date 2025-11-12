# File: main.py (Versione FINALE: Tutti gli UUID a 16-bit standard)
import utime
import ubluetooth 
import struct    
from machine import Pin, I2C
from ssd1306 import SSD1306_I2C
from rotary_irq import RotaryIRQ

# --- Configurazione Hardware (PIN) ---
OLED_WIDTH = 128
OLED_HEIGHT = 64
I2C_BUS = 1
SDA_PIN = 14 
SCL_PIN = 15 
PIN_CLK = 6
PIN_DT = 7
PIN_BUTTON = 8

# --- Variabili Bluetooth (UUID COMPLETAMENTE A 16 BIT) ---
BLE_DEVICE_NAME = "Pico Timer"
# UUID 16-BIT per Servizio (Richiesto per Annuncio funzionante)
_TIMER_SERVICE_UUID_STR = "AAAA" 
# UUID 16-BIT fittizi per Caratteristiche (per evitare EINVAL)
_COMMAND_CHAR_UUID  = ubluetooth.UUID(0xAAAB) # Sostituito con 16-bit
_STATUS_CHAR_UUID   = ubluetooth.UUID(0xAAAC) # Sostituito con 16-bit

# --- Funzione per Creare il Payload di Annuncio (16-bit con Fix Inversione) ---
def create_adv_payload(name, service_uuid_str=None):
    """Costruisce manualmente il payload di annuncio BLE con la struttura corretta."""
    payload = bytearray()
    
    # 1. Flag (Tipo 0x01, Dati: 0x06)
    payload += b'\x02' 
    payload += b'\x01' 
    payload += b'\x06' 

    # 2. Nome del dispositivo (Tipo 0x09 - Nome Completo)
    name_bytes = name.encode('utf-8')
    payload += struct.pack('<B', len(name_bytes) + 1)
    payload += b'\x09' 
    payload += name_bytes

    # 3. UUID di Servizio 16 bit (Tipo 0x03)
    if service_uuid_str and len(service_uuid_str) == 4:
        hex_uuid = service_uuid_str
        
        # FIX: Usa list() e reversed() per invertire i byte
        byte_list = list(bytes.fromhex(hex_uuid))
        service_uuid_16 = bytes(reversed(byte_list))
        
        payload += struct.pack('<B', 3)
        payload += b'\x03' 
        payload += service_uuid_16

    return bytes(payload)


# --- 1. Inizializzazione Display (INVARIATA) ---
print("Inizializzo I2C e Display...")
try:
    i2c = I2C(I2C_BUS, sda=Pin(SDA_PIN), scl=Pin(SCL_PIN), freq=400000)
    display = SSD1306_I2C(OLED_WIDTH, OLED_HEIGHT, i2c)
    display.fill(0)
    display.text("Timer Pronto!", 10, 28) 
    display.show()
    utime.sleep_ms(50) 
except Exception as e:
    print(f"!!! ERRORE DISPLAY: {e}")
    while True: pass

# --- 2. Inizializzazione Bluetooth LE (MODIFICATA) ---
print("Inizializzo Bluetooth...")
try:
    ble = ubluetooth.BLE()
    ble.active(True)

    # USIAMO UUID 16-BIT per la registrazione GATT
    _TIMER_SERVICE_UUID = ubluetooth.UUID(0xAAAA)
    command_char = (_COMMAND_CHAR_UUID, ubluetooth.FLAG_WRITE,)
    status_char = (_STATUS_CHAR_UUID, ubluetooth.FLAG_READ | ubluetooth.FLAG_NOTIFY,)
    timer_service = (_TIMER_SERVICE_UUID, (command_char, status_char),)

    ((cmd_handle, status_handle),) = ble.gatts_register_services((timer_service,))
    
    # Annuncio con funzione custom e UUID 16-bit
    adv_data = create_adv_payload(BLE_DEVICE_NAME, service_uuid_str=_TIMER_SERVICE_UUID_STR)
    ble.gap_advertise(100000, adv_data=adv_data) 
    print("Bluetooth inizializzato.")
    
except Exception as e:
    display.fill(0)
    display.text("BLE FAILED", 30, 28)
    display.show()
    print(f"!!! ERRORE FATALE BLE: {e}")
    while True: pass 

# --- 3. Inizializzazione Encoder e Logica (INVARIANTI) ---
print("Inizializzo Encoder...")
try:
    encoder = RotaryIRQ(pin_num_clk=PIN_CLK, pin_num_dt=PIN_DT, min_val=0, max_val=90, reverse=False, range_mode=RotaryIRQ.RANGE_BOUNDED)
    button = Pin(PIN_BUTTON, Pin.IN, Pin.PULL_UP)
    print("Encoder inizializzato con successo.")
except Exception as e:
    display.fill(0)
    display.text("ENCODER FAILED", 10, 28)
    display.show()
    print(f"!!! ERRORE FATALE ENCODER: {e}")
    while True: pass 

# --- 4. Variabili di Stato (INVARIANTI) ---
STATE_SETTING = "setting"
STATE_COUNTING = "counting"
STATE_FINISHED = "finished"
stato_timer = STATE_SETTING
minuti_impostati = 0
valore_encoder_precedente = encoder.value()
countdown_secondi_totali = 0
tempo_start_timer = 0
secondi_rimanenti_globali = 0 
conn_handle = None 
print("In attesa di connessione BLE...")


# --- 5. Funzioni Helper Display (INVARIANTI) ---
def centra_testo(testo, y):
    x = (OLED_WIDTH - (len(testo) * 8)) // 2
    return max(0, x)

def mostra_schermata_setting(minuti):
    display.fill(0)
    display.text("Imposta Minuti:", centra_testo("Imposta Minuti:", 10), 10)
    testo_minuti = f"{minuti:02d}"
    display.text(testo_minuti, centra_testo(testo_minuti, 35), 35)
    display.text("Premi per START", centra_testo("Premi per START", 55), 55)
    display.show()

def mostra_schermata_countdown(secondi_rimanenti):
    display.fill(0)
    minuti = secondi_rimanenti // 60
    secondi = secondi_rimanenti % 60
    testo_tempo = f"{minuti:02d}:{secondi:02d}"
    display.text(testo_tempo, centra_testo(testo_tempo, 28), 28)
    display.text("Premi x Annulla", 8, 55)
    display.show()

def mostra_schermata_finished():
    display.fill(0)
    display.text("TEMPO", centra_testo("TEMPO", 15), 15)
    display.text("SCADUTO!", centra_testo("SCADUTO!", 35), 35)
    display.text("Premi x Reset", 8, 55)
    display.show()
    for _ in range(3):
        display.invert(1); utime.sleep_ms(150)
        display.invert(0); utime.sleep_ms(150)

# --- 6. Funzioni Bluetooth (INVARIANTI) ---

def invia_stato_ble(stato, secondi_rimanenti):
    global conn_handle
    if conn_handle is not None:
        try:
            stato_id = 0
            if stato == STATE_COUNTING: stato_id = 1
            elif stato == STATE_FINISHED: stato_id = 2
            # B: 1 byte stato ID (0-2), H: 2 byte secondi rimanenti (little-endian)
            data = struct.pack('<BH', stato_id, secondi_rimanenti)
            ble.gatts_notify(conn_handle, status_handle, data)
        except OSError as e:
            conn_handle = None 

def gestisci_comando_ble(data):
    global stato_timer, minuti_impostati, countdown_secondi_totali
    global tempo_start_timer, valore_encoder_precedente, secondi_rimanenti_globali
    
    try:
        cmd = data.decode('utf-8').strip()
        
        if cmd == "START":
            if stato_timer == STATE_SETTING and minuti_impostati > 0:
                countdown_secondi_totali = minuti_impostati * 60
                secondi_rimanenti_globali = countdown_secondi_totali
                tempo_start_timer = utime.ticks_ms()
                stato_timer = STATE_COUNTING
                mostra_schermata_countdown(countdown_secondi_totali)
                
        elif cmd == "STOP" or cmd == "RESET":
            stato_timer = STATE_SETTING
            minuti_impostati = 0
            encoder.set(0)
            valore_encoder_precedente = 0
            secondi_rimanenti_globali = 0
            mostra_schermata_setting(minuti_impostati)
            
        elif cmd.startswith("SET:"):
            try:
                minuti = int(cmd.split(":")[1])
                if 0 <= minuti <= 90:
                    minuti_impostati = minuti
                    encoder.set(minuti)
                    valore_encoder_precedente = minuti
                    secondi_rimanenti_globali = minuti * 60
                    if stato_timer == STATE_SETTING:
                        mostra_schermata_setting(minuti_impostati)
            except (ValueError, IndexError):
                pass
                
    except Exception as e:
        print(f"Errore parsing comando: {e}")

def ble_irq_handler(event, data):
    global conn_handle
    if event == 1: # _IRQ_CENTRAL_CONNECT
        conn_handle, _, _ = data
        print(f"Connesso! Handle: {conn_handle}")
        ble.gap_advertise(None) 
    elif event == 2: # _IRQ_CENTRAL_DISCONNECT
        conn_handle = None
        print("Disconnesso.")
        # Annuncio con funzione custom e UUID 16-bit
        adv_data = create_adv_payload(BLE_DEVICE_NAME, service_uuid_str=_TIMER_SERVICE_UUID_STR)
        ble.gap_advertise(100000, adv_data=adv_data)
    elif event == 3: # _IRQ_GATTS_WRITE
        conn_handle, value_handle = data
        if value_handle == cmd_handle:
            buffer = ble.gatts_read(cmd_handle)
            gestisci_comando_ble(buffer)

ble.irq(ble_irq_handler)

# --- 7. Loop Principale (INVARIANTE) ---
mostra_schermata_setting(minuti_impostati)
ultimo_invio_ble = utime.ticks_ms()

while True:
    
    # --- STATO 1: IMPOSTAZIONE ---
    if stato_timer == STATE_SETTING:
        minuti_impostati = encoder.value()
        if minuti_impostati != valore_encoder_precedente:
            valore_encoder_precedente = minuti_impostati
            secondi_rimanenti_globali = minuti_impostati * 60
            mostra_schermata_setting(minuti_impostati)
            
        if button.value() == 0: 
            utime.sleep_ms(30) 
            if button.value() == 0: 
                if minuti_impostati > 0:
                    countdown_secondi_totali = minuti_impostati * 60
                    secondi_rimanenti_globali = countdown_secondi_totali
                    tempo_start_timer = utime.ticks_ms() 
                    stato_timer = STATE_COUNTING
                    mostra_schermata_countdown(countdown_secondi_totali)
                while button.value() == 0: utime.sleep_ms(10)
    
    # --- STATO 2: COUNTDOWN IN CORSO ---
    elif stato_timer == STATE_COUNTING:
        tempo_trascorso_ms = utime.ticks_diff(utime.ticks_ms(), tempo_start_timer)
        tempo_trascorso_sec = tempo_trascorso_ms // 1000
        secondi_rimanenti = countdown_secondi_totali - tempo_trascorso_sec
        secondi_rimanenti_globali = secondi_rimanenti
        
        if secondi_rimanenti <= 0:
            stato_timer = STATE_FINISHED
            secondi_rimanenti_globali = 0
            mostra_schermata_finished()
        else:
            if (tempo_trascorso_ms // 1000) != ((tempo_trascorso_ms - 100) // 1000):
                 mostra_schermata_countdown(secondi_rimanenti)
        
        if button.value() == 0:
            utime.sleep_ms(30)
            if button.value() == 0:
                stato_timer = STATE_SETTING 
                secondi_rimanenti_globali = minuti_impostati * 60
                encoder.set(minuti_impostati) 
                valore_encoder_precedente = minuti_impostati
                mostra_schermata_setting(minuti_impostati)
                while button.value() == 0: utime.sleep_ms(10) 

    # --- STATO 3: TIMER FINITO ---
    elif stato_timer == STATE_FINISHED:
        if button.value() == 0:
            utime.sleep_ms(30) 
            if button.value() == 0:
                stato_timer = STATE_SETTING 
                minuti_impostati = 0
                encoder.set(0) 
                valore_encoder_precedente = 0
                secondi_rimanenti_globali = 0
                mostra_schermata_setting(minuti_impostati)
                while button.value() == 0: utime.sleep_ms(10) 

    # --- Invio Stato BLE (INVARIANTE) ---
    if conn_handle is not None and utime.ticks_diff(utime.ticks_ms(), ultimo_invio_ble) > 500:
        invia_stato_ble(stato_timer, secondi_rimanenti_globali)
        ultimo_invio_ble = utime.ticks_ms()

    utime.sleep_ms(10)
