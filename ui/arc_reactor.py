        size = min(self.width(), self.height())
        outer = size * 0.42
        core = size * 0.115
        pulse = (sin(self._pulse) + 1.0) * 0.5
        state_text, _ = self.STATES[self._state]

        # Outer metallic reactor body.
        painter.setPen(QPen(QColor("#737a78"), max(8, int(size * 0.025))))
        painter.setBrush(QColor("#242927"))
        painter.drawEllipse(QPointF(0, 0), outer, outer)

        # Metallic inner ring and fine technical rings.
        self._draw_ring(painter, outer * 0.91, max(3, size * 0.008), QColor("#a9afab"))
        self._draw_ring(painter, outer * 0.78, max(2, size * 0.005), QColor("#555d59"))
        self._draw_ring(painter, outer * 0.67, max(2, size * 0.004), QColor("#8a928d"), 8, 78)