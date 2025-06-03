"""
Ejemplo básico para probar la librería ST7796
"""
import time
import sys
import random
sys.path.append('..') # Para permitir importar del directorio padre

from st7796_rpi import ST7796
from st7796_rpi.graphics import Graphics, WHITE, BLACK, RED, GREEN, BLUE, YELLOW

def main():
    try:
        # Inicializar display
        display = ST7796(rotation=3)  # Rotación 3 = horizontal invertido
        graphics = Graphics(display)
        
        # Llenar pantalla
        display.fill_screen(BLACK)
        
        # Dibujar texto centrado
        graphics.draw_centered_text("Librería ST7796", 20, size=2, color=YELLOW)
        graphics.draw_centered_text("para Raspberry Pi", 40, size=2, color=YELLOW)
        
        # Dibujar rectángulos de colores
        graphics.draw_rectangle(20, 70, 90, 60, RED)
        graphics.draw_rectangle(130, 70, 90, 60, GREEN)
        graphics.draw_rectangle(240, 70, 90, 60, BLUE)
        
        # Dibujar etiquetas
        graphics.draw_centered_text("R", 90, size=3, color=WHITE)
        graphics.draw_centered_text("G", 90, size=3, color=WHITE)
        graphics.draw_centered_text("B", 90, size=3, color=WHITE)
        
        # Dibujar un marco
        for i in range(5):
            graphics.draw_rectangle(10+i, 160+i, display.width-20-(i*2), 100-(i*2), YELLOW)
        
        # Dibujar texto dentro del marco
        graphics.draw_text(20, 180, "Esta es una libreria para", 1, WHITE)
        graphics.draw_text(20, 190, "controlar pantallas ST7796", 1, WHITE)
        graphics.draw_text(20, 200, "en Raspberry Pi 4/5", 1, WHITE)
        graphics.draw_text(20, 220, "con gpiod y spidev", 1, WHITE)
        
        # Dibujar cabecera y pie de página
        graphics.draw_header("ST7796 Lib", "TEST")
        graphics.draw_footer()
        
        print("Test completado. Presiona Ctrl+C para salir...")
        while True:
            time.sleep(0.5)
            # Actualizar solo el footer para mostrar la hora en tiempo real
            graphics.draw_footer()
            
    except KeyboardInterrupt:
        print("\nTest interrumpido por el usuario")
    finally:
        # Liberar recursos al terminar
        if 'display' in locals():
            display.close()

if __name__ == "__main__":
    main()