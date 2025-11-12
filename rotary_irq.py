# File: rotary_irq.py
# Gestore per encoder rotativo con interrupt per MicroPython
# Fonte: Adattato da varie implementazioni standard di MicroPython

from machine import Pin

class RotaryIRQ:
    RANGE_UNBOUNDED = 0
    RANGE_WRAP = 1
    RANGE_BOUNDED = 2

    def __init__(self, pin_num_clk, pin_num_dt, min_val=0, max_val=10, reverse=False, range_mode=RANGE_UNBOUNDED):
        self._pin_clk = Pin(pin_num_clk, Pin.IN, Pin.PULL_UP)
        self._pin_dt = Pin(pin_num_dt, Pin.IN, Pin.PULL_UP)
        self._min_val = min_val
        self._max_val = max_val
        self._reverse = reverse
        self._range_mode = range_mode
        self._value = min_val
        
        # Stato per il decoder
        self._state = 0
        
        # Registra gli interrupt
        self._pin_clk.irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING, handler=self._clk_irq)
        self._pin_dt.irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING, handler=self._dt_irq)

    def _clk_irq(self, pin):
        # Leggi i pin in modo atomico (per quanto possibile)
        clk_val = self._pin_clk.value()
        dt_val = self._pin_dt.value()
        
        if self._reverse:
            clk_val, dt_val = dt_val, clk_val

        # Algoritmo di decodifica a 4 stati
        if clk_val == 1 and dt_val == 0:
            self._state = 1
        elif clk_val == 1 and dt_val == 1 and self._state == 1:
            self._state = 2
            self._update_value(1) # Incrementa
        elif clk_val == 0 and dt_val == 1:
            self._state = 3
        elif clk_val == 0 and dt_val == 0 and self._state == 3:
            self._state = 0
            self._update_value(-1) # Decrementa

    def _dt_irq(self, pin):
        # Leggi i pin in modo atomico
        clk_val = self._pin_clk.value()
        dt_val = self._pin_dt.value()
        
        if self._reverse:
            clk_val, dt_val = dt_val, clk_val

        # Algoritmo di decodifica a 4 stati
        if clk_val == 0 and dt_val == 1 and self._state == 2:
            self._state = 3
        elif clk_val == 1 and dt_val == 1 and self._state == 3:
            self._state = 0
            self._update_value(-1) # Decrementa
        elif clk_val == 1 and dt_val == 0 and self._state == 0:
            self._state = 1
        elif clk_val == 0 and dt_val == 0 and self._state == 1:
            self._state = 2
            self._update_value(1) # Incrementa

    def _update_value(self, delta):
        new_value = self._value + delta
        
        if self._range_mode == self.RANGE_BOUNDED:
            if new_value < self._min_val:
                new_value = self._min_val
            elif new_value > self._max_val:
                new_value = self._max_val
        elif self._range_mode == self.RANGE_WRAP:
            if new_value < self._min_val:
                new_value = self._max_val
            elif new_value > self._max_val:
                new_value = self._min_val
                
        self._value = new_value

    def value(self):
        return self._value

    def set(self, value):
        if self._min_val <= value <= self._max_val:
            self._value = value
        else:
            print(f"Valore {value} fuori range ({self._min_val}-{self._max_val})")
