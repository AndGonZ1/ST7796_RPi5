"""
Funciones para dibujar elementos gráficos en pantallas ST7796
"""
from .fonts import FONT_8x8
from datetime import datetime

# Definir colores (formato RGB565)
BLACK = 0x0000
WHITE = 0xFFFF
RED = 0xF800
GREEN = 0x07E0
BLUE = 0x001F
YELLOW = 0xFFE0
CYAN = 0x07FF
MAGENTA = 0xF81F
ORANGE = 0xFD20
GRAY = 0x8410
DARKGREEN = 0x0400

class Graphics:
    """
    Clase para funciones de dibujo en pantallas ST7796
    
    Args:
        display: Instancia de ST7796
    """
    def __init__(self, display):
        self.display = display
        self.char_buffer_cache = {}
    
    def draw_char(self, x, y, char, size=1, color=WHITE, bg_color=BLACK):
        """
        Dibuja un carácter en la pantalla
        
        Args:
            x (int): Coordenada X
            y (int): Coordenada Y
            char (str): Carácter a dibujar
            size (int): Tamaño (1=8 píxeles, 2=16 píxeles, etc.)
            color (int): Color del texto (RGB565)
            bg_color (int): Color de fondo (RGB565)
        """
        char = char.upper()
        if char not in FONT_8x8:
            char = '?'
        
        # Solo cachear números, letras comunes y símbolos que cambian frecuentemente
        use_cache = char in "0123456789:.%ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        cache_key = f"{char}_{size}_{color}_{bg_color}" if use_cache else None
        
        # Usar caché si existe para este carácter
        if use_cache and cache_key in self.char_buffer_cache:
            buffer = self.char_buffer_cache[cache_key]
            w = 8 * size
            h = 8 * size
            self.display.set_address_window(x, y, x+w-1, y+h-1)
            self.display.dc_line.set_value(1)
            self.display.cs_line.set_value(0)
            self.display.spi.writebytes(buffer)
            self.display.cs_line.set_value(1)
            return
        
        # Resto del código igual, pero guardando en caché al final
        w = 8 * size
        h = 8 * size
        self.display.set_address_window(x, y, x+w-1, y+h-1)
        
        self.display.dc_line.set_value(1)
        self.display.cs_line.set_value(0)
        
        color_hi = (color >> 8) & 0xFF
        color_lo = color & 0xFF
        bg_hi = (bg_color >> 8) & 0xFF
        bg_lo = bg_color & 0xFF
        
        buffer = []
        char_data = FONT_8x8[char]
        
        for row in range(8):
            row_data = char_data[row]
            for _ in range(size):
                row_buffer = []
                for col in range(8):
                    pixel_color = [color_hi, color_lo] if (row_data & (1 << (7-col))) else [bg_hi, bg_lo]
                    row_buffer.extend(pixel_color * size)
                buffer.extend(row_buffer)
        
        # Enviar buffer
        self.display.spi.writebytes(buffer)
        self.display.cs_line.set_value(1)
        
        # Guardar en caché si es un carácter frecuente
        if use_cache:
            self.char_buffer_cache[cache_key] = buffer.copy()
    
    def draw_text(self, x, y, text, size=1, color=WHITE, bg_color=BLACK):
        """
        Dibuja texto en la pantalla
        
        Args:
            x (int): Coordenada X
            y (int): Coordenada Y
            text (str): Texto a dibujar
            size (int): Tamaño (1=8 píxeles, 2=16 píxeles, etc.)
            color (int): Color del texto (RGB565)
            bg_color (int): Color de fondo (RGB565)
        """
        cursor_x = x
        cursor_y = y
        char_w = 8 * size
        
        for char in text:
            if char == '\n':  # Nueva línea
                cursor_y += 8 * size
                cursor_x = x
            else:
                self.draw_char(cursor_x, cursor_y, char, size, color, bg_color)
                cursor_x += char_w
                
                # Comprobar si el siguiente carácter se sale de la pantalla
                if cursor_x > self.display.width - char_w:
                    cursor_y += 8 * size
                    cursor_x = x
    
    def draw_centered_text(self, text, y, size=1, color=WHITE, bg_color=BLACK):
        """
        Dibuja texto centrado horizontalmente
        
        Args:
            text (str): Texto a dibujar
            y (int): Coordenada Y
            size (int): Tamaño (1=8 píxeles, 2=16 píxeles, etc.)
            color (int): Color del texto (RGB565)
            bg_color (int): Color de fondo (RGB565)
        """
        text_width = len(text) * 8 * size
        x = (self.display.width - text_width) // 2
        self.draw_text(x, y, text, size, color, bg_color)
    
    def draw_rectangle(self, x, y, width, height, color):
        """
        Dibuja un rectángulo relleno
        
        Args:
            x (int): Coordenada X
            y (int): Coordenada Y
            width (int): Ancho del rectángulo
            height (int): Alto del rectángulo
            color (int): Color del rectángulo (RGB565)
        """
        # Validar límites
        if x < 0:
            width += x
            x = 0
        if y < 0:
            height += y
            y = 0
        if x + width > self.display.width:
            width = self.display.width - x
        if y + height > self.display.height:
            height = self.display.height - y
        
        # Si dimensiones son inválidas, salir
        if width <= 0 or height <= 0:
            return
            
        self.display.set_address_window(x, y, x+width-1, y+height-1)
        
        # Preparar color
        color_hi = (color >> 8) & 0xFF
        color_lo = color & 0xFF
        
        # Enviar color repetidamente
        self.display.dc_line.set_value(1)
        self.display.cs_line.set_value(0)
        
        # Para rectangulos grandes, enviar en bloques para mejorar eficiencia
        if width * height > 100:
            buffer_size = min(1024, width * height)
            buffer = [color_hi, color_lo] * (buffer_size // 2)
            
            pixels = width * height
            for i in range(pixels // (buffer_size // 2)):
                self.display.spi.writebytes(buffer)
            
            remaining = pixels % (buffer_size // 2)
            if remaining > 0:
                buffer = [color_hi, color_lo] * remaining
                self.display.spi.writebytes(buffer)
        else:
            # Para rectangulos pequeños, enviar directamente
            for _ in range(width * height):
                self.display.spi.writebytes([color_hi, color_lo])
        
        self.display.cs_line.set_value(1)
    
    def draw_rectangle_fast(self, x, y, width, height, color):
        """Versión acelerada de draw_rectangle usando implementación optimizada"""
        # Validar límites de pantalla
        if x < 0:
            width += x
            x = 0
        if y < 0:
            height += y
            y = 0
        if x + width > self.display.width:
            width = self.display.width - x
        if y + height > self.display.height:
            height = self.display.height - y
        
        # Si dimensiones son inválidas, salir
        if width <= 0 or height <= 0:
            return
            
        # Usar una ventana de direcciones única para todo el rectángulo
        self.display.set_address_window(x, y, x+width-1, y+height-1)
        
        # Preparar color
        color_hi = (color >> 8) & 0xFF
        color_lo = color & 0xFF
        
        # Configurar para envío de datos
        self.display.dc_line.set_value(1)
        self.display.cs_line.set_value(0)
        
        # Calcular número total de píxeles
        num_pixels = width * height
        
        # Para áreas grandes, enviar en bloques para eficiencia
        if num_pixels > 512:
            # Crear un buffer de tamaño fijo
            buffer = [color_hi, color_lo] * 512
            
            # Cuántas veces enviar el buffer completo
            full_blocks = num_pixels // 512
            # Cuántos píxeles quedan al final
            remaining = num_pixels % 512
            
            # Enviar bloques completos
            for _ in range(full_blocks):
                self.display.spi.writebytes(buffer)
            
            # Enviar píxeles restantes
            if remaining > 0:
                self.display.spi.writebytes([color_hi, color_lo] * remaining)
        else:
            # Para áreas pequeñas, enviar todo de una vez
            self.display.spi.writebytes([color_hi, color_lo] * num_pixels)
        
        # Finalizar transacción
        self.display.cs_line.set_value(1)

    def draw_text_fast(self, x, y, text, size=1, color=WHITE, bg_color=BLACK):
        """
        Dibuja texto con tamaños que permiten fracciones
        
        Args:
            size: Puede ser 1, 1.5, 2, 2.5, etc.
        """
        if not isinstance(size, (int, float)):
            size = 1  # Valor predeterminado si no es número
            
        # Convertir tamaño a valores enteros internos
        size_int = int(size)
        use_fraction = (size != size_int)
        
        char_w = int(8 * size)
        
        for i, char in enumerate(text):
            char_x = x + (i * char_w)
            
            # Si el carácter estaría fuera de la pantalla, salir
            if char_x >= self.display.width:
                break
            
            # Para tamaños fraccionarios como 1.5, usamos un enfoque especial
            if use_fraction:
                # Dibujar con tamaño entero y luego escalar
                self.draw_char(char_x, y, char, size_int+1, color, bg_color)
            else:
                # Usar el método normal para tamaños enteros
                self.draw_char(char_x, y, char, size_int, color, bg_color)
    
    def draw_horizontal_line(self, x, y, width, color):
        """Dibuja una línea horizontal optimizada"""
        self.draw_rectangle_fast(x, y, width, 1, color)
    
    def draw_vertical_line(self, x, y, height, color):
        """Dibuja una línea vertical optimizada"""
        self.draw_rectangle_fast(x, y, 1, height, color)
    
    def draw_section_title(self, x, y, title, color=YELLOW):
        """
        Dibuja un título de sección con subrayado
        
        Args:
            x (int): Coordenada X
            y (int): Coordenada Y
            title (str): Texto del título
            color (int): Color del título (RGB565)
        """
        self.draw_text(x, y, title, 1, color)
        self.draw_horizontal_line(x, y + 10, len(title) * 8, color)
    
    def draw_header(self, text="Header", mode="", bg_color=BLACK, text_color=WHITE):
        """
        Dibuja una cabecera en la parte superior de la pantalla
        
        Args:
            text (str): Texto principal de la cabecera
            mode (str): Texto secundario (alineado a la derecha)
            bg_color (int): Color de fondo (RGB565)
            text_color (int): Color del texto (RGB565)
        """
        # Dibujar fondo
        self.draw_rectangle(0, 0, self.display.width, 30, bg_color)
        
        # Dibujar texto principal
        self.draw_text(10, 10, text, 2, text_color)
        
        # Mostrar modo de operación si se especifica
        if mode:
            mode_text = f"Modo: {mode}"
            mode_x = self.display.width - (len(mode_text) * 8) - 10
            self.draw_text(mode_x, 15, mode_text, 1, text_color)
    
    def draw_footer(self, bg_color=BLACK, text_color=WHITE, line_color=CYAN):
        """
        Dibuja un pie de página con la fecha y hora actual
        
        Args:
            bg_color (int): Color de fondo (RGB565)
            text_color (int): Color del texto (RGB565)
            line_color (int): Color de la línea separadora (RGB565)
        """
        # Dibujar línea separadora
        self.draw_horizontal_line(0, self.display.height - 21, self.display.width, line_color)
        
        # Dibujar fondo
        self.draw_rectangle(0, self.display.height - 20, self.display.width, 20, bg_color)
        
        # Obtener fecha y hora actual
        current_time = datetime.now().strftime("%H:%M:%S")
        current_date = datetime.now().strftime("%d/%m/%Y")
        
        # Mostrar fecha y hora
        self.draw_text(10, self.display.height - 15, current_date, 1, text_color)
        
        # Calcular posición para la hora (alineado a la derecha)
        time_x = self.display.width - (len(current_time) * 8) - 10
        self.draw_text(time_x, self.display.height - 15, current_time, 1, text_color)