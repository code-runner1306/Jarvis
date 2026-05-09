import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QSurfaceFormat
from ui.orb import OrbWindow
from core.engine import JarvisEngine

def main():
    # Setup for transparent OpenGL window
    app = QApplication(sys.argv)
    
    fmt = QSurfaceFormat()
    fmt.setAlphaBufferSize(8)
    fmt.setSamples(4)
    QSurfaceFormat.setDefaultFormat(fmt)
    
    # Initialize UI
    window = OrbWindow()
    window.show()
    
    # Initialize Engine
    engine = JarvisEngine(ui_window=window)
    engine.start()
    
    print("JARVIS is online and listening...")
    
    try:
        sys.exit(app.exec())
    except KeyboardInterrupt:
        engine.stop()
        print("JARVIS is offline.")

if __name__ == "__main__":
    main()
