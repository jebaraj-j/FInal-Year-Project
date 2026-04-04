"""ui/notification.py — Floating corner notification widget."""

from PyQt5.QtWidgets import QWidget, QLabel, QHBoxLayout
from PyQt5.QtCore    import Qt, QTimer, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt5.QtGui     import QPainter, QColor, QFont


class NotificationWidget(QWidget):
    """Small floating notification that fades in, stays, then fades out."""

    def __init__(self, parent, message: str, icon: str = "✅"):
        super().__init__(parent, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self._opacity = 0.0

        # Layout
        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 8, 14, 8)
        lay.setSpacing(8)

        icon_lbl = QLabel(icon)
        icon_lbl.setFont(QFont("Segoe UI Emoji", 14))
        icon_lbl.setStyleSheet("color: #FFFFFF;")

        msg_lbl = QLabel(message)
        msg_lbl.setFont(QFont("Segoe UI", 10, QFont.Bold))
        msg_lbl.setStyleSheet("color: #FFFFFF;")

        lay.addWidget(icon_lbl)
        lay.addWidget(msg_lbl)
        self.adjustSize()

        # Position bottom-right of parent
        self._reposition()

        # Fade in → hold → fade out
        self._fade(0.0, 1.0, 250, self._hold)

    def _reposition(self):
        if self.parent():
            pr = self.parent().rect()
            self.move(pr.right() - self.width() - 14,
                      pr.bottom() - self.height() - 14)

    def _hold(self):
        QTimer.singleShot(1800, lambda: self._fade(1.0, 0.0, 400, self.close))

    def _fade(self, start, end, duration, callback=None):
        self._anim = QPropertyAnimation(self, b"opacity")
        self._anim.setDuration(duration)
        self._anim.setStartValue(start)
        self._anim.setEndValue(end)
        self._anim.setEasingCurve(QEasingCurve.InOutQuad)
        if callback:
            self._anim.finished.connect(callback)
        self._anim.start()
        self.show()

    @pyqtProperty(float)
    def opacity(self):
        return self._opacity

    @opacity.setter
    def opacity(self, value):
        self._opacity = value
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setOpacity(self._opacity)
        p.setBrush(QColor(13, 71, 161, 230))   # deep blue
        p.setPen(QColor(66, 165, 245, 200))
        p.drawRoundedRect(self.rect(), 10, 10)
        super().paintEvent(event)
