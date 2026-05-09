import sys
import time
import numpy as np
from PySide6.QtCore import Qt, QTimer, Slot
from PySide6.QtWidgets import QApplication, QMainWindow, QOpenGLWidget
from PySide6.QtGui import QSurfaceFormat
import moderngl

class OrbWidget(QOpenGLWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ctx = None
        self.prog = None
        self.vbo = None
        self.vao = None
        self.start_time = time.time()
        self.volume = 0.0
        
        # Set transparent background
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        
        # Timer for updates
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update)
        self.timer.start(16)  # ~60 FPS

    def initializeGL(self):
        self.ctx = moderngl.create_context()
        
        # Simple vertex shader (full screen quad)
        v_shader = """
        #version 330
        in vec2 in_vert;
        void main() {
            gl_Position = vec4(in_vert, 0.0, 1.0);
        }
        """
        
        # Load fragment shader
        with open("ui/shaders/orb.frag", "r") as f:
            f_shader = f.read()
            
        self.prog = self.ctx.program(vertex_shader=v_shader, fragment_shader=f_shader)
        
        # Full screen quad coordinates
        vertices = np.array([
            -1.0, -1.0,
             1.0, -1.0,
            -1.0,  1.0,
             1.0,  1.0,
        ], dtype='f4')
        
        self.vbo = self.ctx.buffer(vertices)
        self.vao = self.ctx.simple_vertex_array(self.prog, self.vbo, 'in_vert')

    def paintGL(self):
        self.ctx.clear(0.0, 0.0, 0.0, 0.0)
        
        # Update uniforms
        current_time = time.time() - self.start_time
        
        try:
            self.prog['time'].value = current_time
            self.prog['volume'].value = self.volume
            self.prog['resolution'].value = (self.width(), self.height())
        except KeyError:
            pass # Uniforms might be optimized out if unused
            
        self.vao.render(moderngl.TRIANGLE_STRIP)

    def set_volume(self, vol):
        # Smooth the volume input a bit
        self.volume = self.volume * 0.7 + vol * 0.3

class OrbWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.orb = OrbWidget(self)
        self.setCentralWidget(self.orb)
        self.resize(800, 800)
        self.setWindowTitle("JARVIS Orb")
        
        # Make background transparent
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        
        # Center on screen
        screen = QApplication.primaryScreen().geometry()
        self.move((screen.width() - self.width()) // 2, (screen.height() - self.height()) // 2)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Enable transparency
    fmt = QSurfaceFormat()
    fmt.setAlphaBufferSize(8)
    QSurfaceFormat.setDefaultFormat(fmt)
    
    window = OrbWindow()
    window.show()
    sys.exit(app.exec())
