"""
Clase principal que maneja la comunicación con la pantalla ST7796
"""
import time
import spidev
import sys
import platform
import os

# Intentar cargar los módulos GPIO según disponibilidad
GPIO = None

# Función para detectar automáticamente la plataforma de hardware
def detect_rpi_model():
    try:
        with open('/proc/device-tree/model', 'r') as f:
            model = f.read()
            if '5' in model:
                return 5
            elif '4' in model:
                return 4
            else:
                return 3  # Suponemos 3 como predeterminado para modelos anteriores
    except:
        # Si no podemos detectar, asumimos 4 por seguridad
        return 4

def import_gpio():
    global GPIO
    try:
        # Intentar primero con RPi.GPIO (funciona en la mayoría de los casos)
        import RPi.GPIO as GPIO
        return "RPi.GPIO"
    except ImportError:
        try:
            # Intentar con gpiod como alternativa
            import gpiod
            return "gpiod"
        except ImportError:
            try:
                # Último intento con lgpio (Raspberry Pi 5)
                import lgpio
                return "lgpio"
            except ImportError:
                print("ERROR: No se pudo cargar ningún módulo GPIO compatible")
                sys.exit(1)

from .graphics import (
    BLACK, WHITE, RED, GREEN, BLUE, 
    YELLOW, CYAN, MAGENTA, GRAY, ORANGE, DARKGREEN
)

class ST7796:
    """
    Controlador para pantallas con chip ST7796
    
    Args:
        width (int): Ancho de la pantalla en píxeles
        height (int): Alto de la pantalla en píxeles
        rotation (int): Rotación de la pantalla (0-3)
        dc_pin (int): Pin de Data/Command (GPIO)
        rst_pin (int): Pin de Reset (GPIO)
        cs_pin (int): Pin de Chip Select (GPIO)
        spi_speed_hz (int): Velocidad SPI en Hz
    """
    def __init__(self, width=320, height=480, rotation=0, 
                 dc_pin=5, rst_pin=6, cs_pin=22, 
                 spi_speed_hz=80000000, gpio_chip=None):
        # Configuración de pantalla
        self.width = width
        self.height = height
        
        # Configuración de pines
        self.dc_pin = dc_pin
        self.rst_pin = rst_pin
        self.cs_pin = cs_pin
        
        # Detectar plataforma y módulo GPIO
        self.rpi_model = detect_rpi_model() if os.name != 'nt' else 0
        self.gpio_module = import_gpio() if os.name != 'nt' else "DUMMY"
        
        print(f"Modelo RPi detectado: {self.rpi_model}")
        print(f"Módulo GPIO: {self.gpio_module}")
        
        # Inicializar GPIO
        self._init_gpio(gpio_chip)
        
        # Inicializar SPI
        self._init_spi(spi_speed_hz)
        
        # Inicializar pantalla
        self.reset()
        self._init_display()
        self.set_rotation(rotation)
        
        # Caché para caracteres
        self.char_buffer_cache = {}
    
    def _init_gpio(self, gpio_chip):
        """Inicializa los pines GPIO utilizando el módulo disponible"""
        try:
            if self.gpio_module == "RPi.GPIO":
                # Inicialización con RPi.GPIO
                import RPi.GPIO as GPIO
                GPIO.setmode(GPIO.BCM)
                GPIO.setwarnings(False)
                
                # Configurar pines como salidas
                GPIO.setup(self.dc_pin, GPIO.OUT)
                GPIO.setup(self.rst_pin, GPIO.OUT)
                GPIO.setup(self.cs_pin, GPIO.OUT)
                
                # Establecer niveles iniciales
                GPIO.output(self.dc_pin, GPIO.HIGH)
                GPIO.output(self.rst_pin, GPIO.HIGH)
                GPIO.output(self.cs_pin, GPIO.HIGH)
                
                # Guardar referencia a GPIO para métodos
                self.GPIO = GPIO
                print("GPIO inicializado con RPi.GPIO")
                
            elif self.gpio_module == "gpiod":
                # Inicialización con gpiod
                import gpiod
                
                # Intentar auto-detectar el chip GPIO adecuado
                if gpio_chip is None:
                    try:
                        # RPi 5 usa gpiochip4
                        if self.rpi_model == 5:
                            self.chip = gpiod.Chip('gpiochip4')
                            print("Usando gpiochip4 (RPi 5)")
                        else:
                            # RPi 4 y anteriores usan gpiochip0
                            self.chip = gpiod.Chip('gpiochip0')
                            print("Usando gpiochip0 (RPi 4 o anterior)")
                    except Exception:
                        # Si falla, intentar con gpiochip0 como último recurso
                        self.chip = gpiod.Chip('gpiochip0')
                else:
                    self.chip = gpiod.Chip(gpio_chip)
                
                # Configurar líneas GPIO
                self.dc_line = self.chip.get_line(self.dc_pin)
                self.rst_line = self.chip.get_line(self.rst_pin)
                self.cs_line = self.chip.get_line(self.cs_pin)
                
                # Solicitar líneas para salida
                self.dc_line.request(consumer="st7796", type=gpiod.LINE_REQ_DIR_OUT)
                self.rst_line.request(consumer="st7796", type=gpiod.LINE_REQ_DIR_OUT)
                self.cs_line.request(consumer="st7796", type=gpiod.LINE_REQ_DIR_OUT)
                print("GPIO inicializado con gpiod")
                
            elif self.gpio_module == "lgpio":
                # Inicialización con lgpio (para RPi 5)
                import lgpio
                
                self.gpio_handle = lgpio.gpiochip_open(4 if self.rpi_model == 5 else 0)
                
                # Configurar pines como salidas
                lgpio.gpio_claim_output(self.gpio_handle, self.dc_pin)
                lgpio.gpio_claim_output(self.gpio_handle, self.rst_pin)
                lgpio.gpio_claim_output(self.gpio_handle, self.cs_pin)
                
                # Establecer niveles iniciales
                lgpio.gpio_write(self.gpio_handle, self.dc_pin, 1)
                lgpio.gpio_write(self.gpio_handle, self.rst_pin, 1)
                lgpio.gpio_write(self.gpio_handle, self.cs_pin, 1)
                
                # Guardar referencia a lgpio
                self.lgpio = lgpio
                print("GPIO inicializado con lgpio")
            
            elif self.gpio_module == "DUMMY":
                # Para desarrollo en sistemas no-RPi
                print("Modo de simulación GPIO (no RPi)")
                
            else:
                raise Exception("Módulo GPIO no soportado")
                
        except Exception as e:
            print(f"Error al inicializar GPIO: {e}")
            sys.exit(1)
    
    def _init_spi(self, spi_speed_hz):
        """Inicializa el bus SPI"""
        try:
            if os.name == 'nt':
                # Modo de simulación para sistemas no-RPi
                print("Modo de simulación SPI (no RPi)")
                return
                
            self.spi = spidev.SpiDev()
            self.spi.open(0, 0)  # Bus 0, dispositivo 0
            self.spi.max_speed_hz = spi_speed_hz
            self.spi.mode = 0
            print(f"SPI inicializado a {spi_speed_hz/1000000:.1f} MHz")
        except Exception as e:
            print(f"Error al inicializar SPI: {e}")
            sys.exit(1)
    
    def write_cmd(self, cmd):
        """Envía un comando a la pantalla"""
        if self.gpio_module == "RPi.GPIO":
            self.GPIO.output(self.dc_pin, self.GPIO.LOW)  # Comando
            self.GPIO.output(self.cs_pin, self.GPIO.LOW)  # Seleccionar chip
            self.spi.writebytes([cmd])
            self.GPIO.output(self.cs_pin, self.GPIO.HIGH)  # Deseleccionar chip
            
        elif self.gpio_module == "gpiod":
            self.dc_line.set_value(0)  # Comando
            self.cs_line.set_value(0)  # Seleccionar chip
            self.spi.writebytes([cmd])
            self.cs_line.set_value(1)  # Deseleccionar chip
            
        elif self.gpio_module == "lgpio":
            self.lgpio.gpio_write(self.gpio_handle, self.dc_pin, 0)  # Comando
            self.lgpio.gpio_write(self.gpio_handle, self.cs_pin, 0)  # Seleccionar chip
            self.spi.writebytes([cmd])
            self.lgpio.gpio_write(self.gpio_handle, self.cs_pin, 1)  # Deseleccionar chip
            
        elif self.gpio_module == "DUMMY":
            # Modo simulación
            pass
    
    def write_data(self, data):
        """Envía datos a la pantalla"""
        if self.gpio_module == "RPi.GPIO":
            self.GPIO.output(self.dc_pin, self.GPIO.HIGH)  # Datos
            self.GPIO.output(self.cs_pin, self.GPIO.LOW)  # Seleccionar chip
            
            if isinstance(data, list):
                self.spi.writebytes(data)
            else:
                self.spi.writebytes([data])
                
            self.GPIO.output(self.cs_pin, self.GPIO.HIGH)  # Deseleccionar chip
            
        elif self.gpio_module == "gpiod":
            self.dc_line.set_value(1)  # Datos
            self.cs_line.set_value(0)  # Seleccionar chip
            
            if isinstance(data, list):
                self.spi.writebytes(data)
            else:
                self.spi.writebytes([data])
                
            self.cs_line.set_value(1)  # Deseleccionar chip
            
        elif self.gpio_module == "lgpio":
            self.lgpio.gpio_write(self.gpio_handle, self.dc_pin, 1)  # Datos
            self.lgpio.gpio_write(self.gpio_handle, self.cs_pin, 0)  # Seleccionar chip
            
            if isinstance(data, list):
                self.spi.writebytes(data)
            else:
                self.spi.writebytes([data])
                
            self.lgpio.gpio_write(self.gpio_handle, self.cs_pin, 1)  # Deseleccionar chip
            
        elif self.gpio_module == "DUMMY":
            # Modo simulación
            pass
    
    def reset(self):
        """Resetea la pantalla mediante el pin de reset"""
        print("Reseteando pantalla...")
        
        if self.gpio_module == "RPi.GPIO":
            self.GPIO.output(self.rst_pin, self.GPIO.HIGH)
            time.sleep(0.05)
            self.GPIO.output(self.rst_pin, self.GPIO.LOW)
            time.sleep(0.1)
            self.GPIO.output(self.rst_pin, self.GPIO.HIGH)
            
        elif self.gpio_module == "gpiod":
            self.rst_line.set_value(1)
            time.sleep(0.05)
            self.rst_line.set_value(0)
            time.sleep(0.1)
            self.rst_line.set_value(1)
            
        elif self.gpio_module == "lgpio":
            self.lgpio.gpio_write(self.gpio_handle, self.rst_pin, 1)
            time.sleep(0.05)
            self.lgpio.gpio_write(self.gpio_handle, self.rst_pin, 0)
            time.sleep(0.1)
            self.lgpio.gpio_write(self.gpio_handle, self.rst_pin, 1)
            
        elif self.gpio_module == "DUMMY":
            # Modo simulación
            pass
            
        time.sleep(0.05)
    
    def _init_display(self):
        """Inicializa la pantalla con la secuencia para ST7796"""
        print("Inicializando ST7796...")
        
        # Sleep Out
        self.write_cmd(0x11)
        time.sleep(0.12)
        
        # Configuración básica de la pantalla
        self.write_cmd(0x36)
        self.write_data(0x48)
        
        self.write_cmd(0x3A)
        self.write_data(0x55)  # 16 bits por pixel (RGB565)
        
        # Secuencia de inicialización para ST7796
        self.write_cmd(0xF0)
        self.write_data(0xC3)
        
        self.write_cmd(0xF0)
        self.write_data(0x96)
        
        self.write_cmd(0xB4)
        self.write_data(0x02)
        
        self.write_cmd(0xB7)
        self.write_data(0xC6)
        
        self.write_cmd(0xC0)
        self.write_data(0xC0)
        self.write_data(0x00)
        
        self.write_cmd(0xC1)
        self.write_data(0x13)
        
        self.write_cmd(0xC2)
        self.write_data(0xA7)
        
        self.write_cmd(0xC5)
        self.write_data(0x21)
        
        self.write_cmd(0xE8)
        self.write_data(0x40)
        self.write_data(0x8A)
        self.write_data(0x1B)
        self.write_data(0x1B)
        self.write_data(0x23)
        self.write_data(0x0A)
        self.write_data(0xAC)
        self.write_data(0x33)
        
        # Gamma settings
        self.write_cmd(0xE0)  # Positive Gamma
        self.write_data(0xD2)
        self.write_data(0x05)
        self.write_data(0x08)
        self.write_data(0x06)
        self.write_data(0x05)
        self.write_data(0x02)
        self.write_data(0x2A)
        self.write_data(0x44)
        self.write_data(0x46)
        self.write_data(0x39)
        self.write_data(0x15)
        self.write_data(0x15)
        self.write_data(0x2D)
        self.write_data(0x32)
        
        self.write_cmd(0xE1)  # Negative Gamma
        self.write_data(0x96)
        self.write_data(0x08)
        self.write_data(0x0C)
        self.write_data(0x09)
        self.write_data(0x09)
        self.write_data(0x25)
        self.write_data(0x2E)
        self.write_data(0x43)
        self.write_data(0x42)
        self.write_data(0x35)
        self.write_data(0x11)
        self.write_data(0x11)
        self.write_data(0x28)
        self.write_data(0x2E)
        
        self.write_cmd(0xF0)
        self.write_data(0x3C)
        
        self.write_cmd(0xF0)
        self.write_data(0x69)
        
        time.sleep(0.12)
        
        # Encender la pantalla
        self.write_cmd(0x21)  # Display Inversion On
        self.write_cmd(0x29)  # Display On
        
        print("Inicialización completa")
    
    def set_rotation(self, rotation):
        """
        Establece la orientación de la pantalla
        
        Args:
            rotation (int): Orientación (0-3)
                0: 0 grados
                1: 90 grados
                2: 180 grados
                3: 270 grados
        """
        rotation = rotation % 4
        self.write_cmd(0x36)
        
        if rotation == 0:  # 0 grados
            self.write_data(0x48)
            self.width, self.height = 320, 480
        elif rotation == 1:  # 90 grados
            self.write_data(0x28)
            self.width, self.height = 480, 320
        elif rotation == 2:  # 180 grados
            self.write_data(0x88)
            self.width, self.height = 320, 480
        elif rotation == 3:  # 270 grados
            self.write_data(0xE8)
            self.width, self.height = 480, 320
            
        print(f"Pantalla configurada en rotación {rotation}, tamaño: {self.width}x{self.height}")
    
    def set_address_window(self, x0, y0, x1, y1):
        """
        Establece ventana de dibujo para enviar píxeles
        
        Args:
            x0 (int): Coordenada X inicio
            y0 (int): Coordenada Y inicio
            x1 (int): Coordenada X fin
            y1 (int): Coordenada Y fin
        """
        # Column Address Set
        self.write_cmd(0x2A)
        self.write_data(x0 >> 8)
        self.write_data(x0 & 0xFF)
        self.write_data(x1 >> 8)
        self.write_data(x1 & 0xFF)
        
        # Row Address Set
        self.write_cmd(0x2B)
        self.write_data(y0 >> 8)
        self.write_data(y0 & 0xFF)
        self.write_data(y1 >> 8)
        self.write_data(y1 & 0xFF)
        
        # Memory Write
        self.write_cmd(0x2C)
    
    def set_address_window_fast(self, x0, y0, x1, y1):
        """Versión optimizada de set_address_window con menos transacciones SPI"""
        # Column Address Set
        self.write_cmd(0x2A)
        # Envía todos los datos de una sola vez
        self.write_data([
            x0 >> 8, x0 & 0xFF,
            x1 >> 8, x1 & 0xFF
        ])
        
        # Row Address Set
        self.write_cmd(0x2B)
        self.write_data([
            y0 >> 8, y0 & 0xFF,
            y1 >> 8, y1 & 0xFF
        ])
        
        # Memory Write
        self.write_cmd(0x2C)
    
    def fill_screen(self, color):
        """
        Llena toda la pantalla con un color específico
        
        Args:
            color (int): Color en formato RGB565
        """
        self.set_address_window(0, 0, self.width-1, self.height-1)
        
        # Preparar color
        color_high = (color >> 8) & 0xFF
        color_low = color & 0xFF
        
        if self.gpio_module == "DUMMY":
            # Modo simulación
            print(f"Simulación: Pantalla llena con color 0x{color:04X}")
            return
        
        # Configurar para envío de datos
        if self.gpio_module == "RPi.GPIO":
            self.GPIO.output(self.dc_pin, self.GPIO.HIGH)  # Datos
            self.GPIO.output(self.cs_pin, self.GPIO.LOW)   # Seleccionar chip
        elif self.gpio_module == "gpiod":
            self.dc_line.set_value(1)  # Datos
            self.cs_line.set_value(0)  # Seleccionar chip
        elif self.gpio_module == "lgpio":
            self.lgpio.gpio_write(self.gpio_handle, self.dc_pin, 1)  # Datos
            self.lgpio.gpio_write(self.gpio_handle, self.cs_pin, 0)  # Seleccionar chip
        
        # Enviamos el color en bloques para mayor eficiencia
        buffer_size = 1024
        buffer = [color_high, color_low] * (buffer_size // 2)
        
        pixels = self.width * self.height
        for i in range(pixels // (buffer_size // 2)):
            self.spi.writebytes(buffer)
        
        remaining = pixels % (buffer_size // 2)
        if remaining > 0:
            buffer = [color_high, color_low] * remaining
            self.spi.writebytes(buffer)
        
        # Deseleccionar chip
        if self.gpio_module == "RPi.GPIO":
            self.GPIO.output(self.cs_pin, self.GPIO.HIGH)
        elif self.gpio_module == "gpiod":
            self.cs_line.set_value(1)
        elif self.gpio_module == "lgpio":
            self.lgpio.gpio_write(self.gpio_handle, self.cs_pin, 1)
    
    def draw_pixel(self, x, y, color):
        """
        Dibuja un píxel en la posición especificada
        
        Args:
            x (int): Coordenada X
            y (int): Coordenada Y
            color (int): Color en formato RGB565
        """
        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            return  # Fuera de los límites
            
        self.set_address_window(x, y, x, y)
        
        # Modo simulación
        if self.gpio_module == "DUMMY":
            return
        
        # Enviar color según el módulo GPIO
        if self.gpio_module == "RPi.GPIO":
            self.GPIO.output(self.dc_pin, self.GPIO.HIGH)  # Datos
            self.GPIO.output(self.cs_pin, self.GPIO.LOW)   # Seleccionar chip
            self.spi.writebytes([(color >> 8) & 0xFF, color & 0xFF])
            self.GPIO.output(self.cs_pin, self.GPIO.HIGH)  # Deseleccionar chip
        elif self.gpio_module == "gpiod":
            self.dc_line.set_value(1)  # Datos
            self.cs_line.set_value(0)  # Seleccionar chip
            self.spi.writebytes([(color >> 8) & 0xFF, color & 0xFF])
            self.cs_line.set_value(1)  # Deseleccionar chip
        elif self.gpio_module == "lgpio":
            self.lgpio.gpio_write(self.gpio_handle, self.dc_pin, 1)  # Datos
            self.lgpio.gpio_write(self.gpio_handle, self.cs_pin, 0)  # Seleccionar chip
            self.spi.writebytes([(color >> 8) & 0xFF, color & 0xFF])
            self.lgpio.gpio_write(self.gpio_handle, self.cs_pin, 1)  # Deseleccionar chip

    def draw_rectangle_optimized(self, x, y, width, height, color):
        """Versión optimizada que reduce el número de transacciones SPI"""
        # Validar límites
        if x < 0:
            width += x
            x = 0
        if y < 0:
            height += y
            y = 0
        if x + width > self.width:
            width = self.width - x
        if y + height > self.height:
            height = self.height - y
    
        # Si dimensiones son inválidas, salir
        if width <= 0 or height <= 0:
            return
            
        self.set_address_window_fast(x, y, x+width-1, y+height-1)
        
        # Modo simulación
        if self.gpio_module == "DUMMY":
            print(f"Simulación: Rectángulo en ({x},{y}) tamaño {width}x{height} color 0x{color:04X}")
            return
        
        # Preparar color
        color_hi = (color >> 8) & 0xFF
        color_lo = color & 0xFF
        
        # Establecer pines según el módulo GPIO
        if self.gpio_module == "RPi.GPIO":
            self.GPIO.output(self.dc_pin, self.GPIO.HIGH)  # Datos
            self.GPIO.output(self.cs_pin, self.GPIO.LOW)   # Seleccionar chip
        elif self.gpio_module == "gpiod":
            self.dc_line.set_value(1)  # Datos
            self.cs_line.set_value(0)  # Seleccionar chip
        elif self.gpio_module == "lgpio":
            self.lgpio.gpio_write(self.gpio_handle, self.dc_pin, 1)  # Datos
            self.lgpio.gpio_write(self.gpio_handle, self.cs_pin, 0)  # Seleccionar chip
        
        # Crear un buffer único para toda la operación
        pixel_count = width * height
        
        # Para rectángulos grandes, usar buffers de tamaño fijo
        if pixel_count > 1024:
            buffer = [color_hi, color_lo] * 512  # 1024 bytes
            full_writes = pixel_count // 512
            remainder = pixel_count % 512
            
            # Enviar bloques completos
            for _ in range(full_writes):
                self.spi.writebytes(buffer)
            
            # Enviar el resto
            if remainder > 0:
                self.spi.writebytes([color_hi, color_lo] * remainder)
        else:
            # Para rectángulos pequeños, un solo buffer
            buffer = [color_hi, color_lo] * pixel_count
            self.spi.writebytes(buffer)
        
        # Deseleccionar chip según el módulo GPIO
        if self.gpio_module == "RPi.GPIO":
            self.GPIO.output(self.cs_pin, self.GPIO.HIGH)
        elif self.gpio_module == "gpiod":
            self.cs_line.set_value(1)
        elif self.gpio_module == "lgpio":
            self.lgpio.gpio_write(self.gpio_handle, self.cs_pin, 1)

    def close(self):
        """Libera los recursos utilizados"""
        try:
            if self.gpio_module == "DUMMY":
                print("Simulación: Recursos liberados")
                return
                
            if hasattr(self, 'spi'):
                self.spi.close()
                
            if self.gpio_module == "RPi.GPIO":
                self.GPIO.cleanup([self.dc_pin, self.rst_pin, self.cs_pin])
            elif self.gpio_module == "gpiod":
                self.dc_line.release()
                self.rst_line.release()
                self.cs_line.release()
            elif self.gpio_module == "lgpio":
                self.lgpio.gpio_free(self.gpio_handle, self.dc_pin)
                self.lgpio.gpio_free(self.gpio_handle, self.rst_pin)
                self.lgpio.gpio_free(self.gpio_handle, self.cs_pin)
                self.lgpio.gpiochip_close(self.gpio_handle)
                
            print("Recursos liberados correctamente")
        except Exception as e:
            print(f"Error al liberar recursos: {e}")