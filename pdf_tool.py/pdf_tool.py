import sys
import pymupdf
from PyQt6.QtWidgets import (QApplication, QMainWindow, QLabel, QVBoxLayout,
                             QPushButton, QWidget, QFileDialog, QRubberBand,
                             QScrollArea, QMessageBox, QHBoxLayout)
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtCore import Qt, QRect, QPoint

class PDFViewerLabel(QLabel):
    """Кастомный виджет для отображения PDF и выделения области мышкой."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.rubber_band = QRubberBand(QRubberBand.Shape.Rectangle, self)
        self.origin = QPoint()
        self.selected_rect = QRect()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.origin = event.pos()
            self.rubber_band.setGeometry(QRect(self.origin, self.origin))
            self.rubber_band.show()

    def mouseMoveEvent(self, event):
        if not self.origin.isNull():
            self.rubber_band.setGeometry(QRect(self.origin, event.pos()).normalized())

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.selected_rect = self.rubber_band.geometry()

class PDFApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PDF Tool (Fedora Plasma 6) - Zoom & Navigation")
        self.resize(1100, 900)

        self.doc = None
        self.current_page = None
        self.current_page_index = 0  # Отслеживаем текущую страницу
        self.total_pages = 0         # Всего страниц в документе

        self.zoom_factor = 1.0
        self.scale_x = 1.0
        self.scale_y = 1.0

        self.init_ui()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # 1. Верхняя панель: Основные инструменты
        top_btn_layout = QHBoxLayout()

        self.btn_open = QPushButton("Открыть PDF")
        self.btn_open.clicked.connect(self.open_pdf)

        self.btn_zoom_out = QPushButton("- Зум")
        self.btn_zoom_out.clicked.connect(self.zoom_out)
        self.btn_zoom_out.setEnabled(False)

        self.btn_zoom_in = QPushButton("+ Зум")
        self.btn_zoom_in.clicked.connect(self.zoom_in)
        self.btn_zoom_in.setEnabled(False)

        self.btn_highlight = QPushButton("Выделить (маркер)")
        self.btn_highlight.clicked.connect(self.highlight_text)
        self.btn_highlight.setEnabled(False)

        self.btn_redact = QPushButton("Закрасить (черный)")
        self.btn_redact.clicked.connect(self.redact_text)
        self.btn_redact.setEnabled(False)

        self.btn_crop = QPushButton("Вырезать часть")
        self.btn_crop.clicked.connect(self.crop_pdf)
        self.btn_crop.setEnabled(False)

        self.btn_save = QPushButton("Сохранить PDF")
        self.btn_save.clicked.connect(self.save_pdf)
        self.btn_save.setEnabled(False)

        top_btn_layout.addWidget(self.btn_open)
        top_btn_layout.addWidget(self.btn_zoom_out)
        top_btn_layout.addWidget(self.btn_zoom_in)
        top_btn_layout.addWidget(self.btn_highlight)
        top_btn_layout.addWidget(self.btn_redact)
        top_btn_layout.addWidget(self.btn_crop)
        top_btn_layout.addWidget(self.btn_save)
        layout.addLayout(top_btn_layout)

        # 2. Вторая панель: Навигация по страницам
        nav_layout = QHBoxLayout()

        self.btn_prev_page = QPushButton("◀ Назад")
        self.btn_prev_page.clicked.connect(self.prev_page)
        self.btn_prev_page.setEnabled(False)

        self.label_page_info = QLabel("Страница: 0 / 0")
        self.label_page_info.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.btn_next_page = QPushButton("Вперед ▶")
        self.btn_next_page.clicked.connect(self.next_page)
        self.btn_next_page.setEnabled(False)

        nav_layout.addWidget(self.btn_prev_page)
        nav_layout.addWidget(self.label_page_info)
        nav_layout.addWidget(self.btn_next_page)

        # Добавляем панель навигации под основными кнопками
        layout.addLayout(nav_layout)

        # 3. Область для отображения PDF
        self.scroll_area = QScrollArea()
        self.viewer_label = PDFViewerLabel()
        self.viewer_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        self.scroll_area.setWidget(self.viewer_label)
        self.scroll_area.setWidgetResizable(True)
        layout.addWidget(self.scroll_area)

    def open_pdf(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите PDF", "", "PDF Files (*.pdf)"
        )
        if file_path:
            self.doc = pymupdf.open(file_path)
            self.total_pages = len(self.doc)
            self.current_page_index = 0
            self.zoom_factor = 1.0

            self.load_current_page()

            # Активируем инструменты
            self.btn_zoom_in.setEnabled(True)
            self.btn_zoom_out.setEnabled(True)
            self.btn_highlight.setEnabled(True)
            self.btn_redact.setEnabled(True)
            self.btn_crop.setEnabled(True)
            self.btn_save.setEnabled(True)

    def load_current_page(self):
        """Загружает страницу по индексу, рендерит её и обновляет UI навигации."""
        self.current_page = self.doc[self.current_page_index]
        self.render_page()
        self.update_nav_ui()

    def update_nav_ui(self):
        """Обновляет текст метки и включает/выключает кнопки навигации."""
        self.label_page_info.setText(f"Страница: {self.current_page_index + 1} / {self.total_pages}")

        # Кнопка 'Назад' активна только если мы не на первой странице
        self.btn_prev_page.setEnabled(self.current_page_index > 0)

        # Кнопка 'Вперед' активна только если мы не на последней странице
        self.btn_next_page.setEnabled(self.current_page_index < self.total_pages - 1)

    def prev_page(self):
        if self.current_page_index > 0:
            self.current_page_index -= 1
            self.load_current_page()
            # Прокручиваем область просмотра наверх при смене страницы
            self.scroll_area.verticalScrollBar().setValue(0)

    def next_page(self):
        if self.current_page_index < self.total_pages - 1:
            self.current_page_index += 1
            self.load_current_page()
            # Прокручиваем область просмотра наверх при смене страницы
            self.scroll_area.verticalScrollBar().setValue(0)

    def zoom_in(self):
        self.zoom_factor *= 1.25
        self.render_page()

    def zoom_out(self):
        self.zoom_factor *= 0.8
        self.render_page()

    def render_page(self):
        if not self.current_page:
            return

        mat = pymupdf.Matrix(self.zoom_factor, self.zoom_factor)
        pix = self.current_page.get_pixmap(matrix=mat, alpha=False)

        qimg = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888)
        self.viewer_label.setPixmap(QPixmap.fromImage(qimg))
        self.viewer_label.resize(pix.width, pix.height)

        self.scale_x = self.current_page.rect.width / pix.width
        self.scale_y = self.current_page.rect.height / pix.height

        self.viewer_label.rubber_band.hide()
        self.viewer_label.selected_rect = QRect()

    def get_pdf_rect_from_ui(self):
        rect = self.viewer_label.selected_rect
        if rect.isEmpty():
            return None

        x0 = rect.left() * self.scale_x
        y0 = rect.top() * self.scale_y
        x1 = rect.right() * self.scale_x
        y1 = rect.bottom() * self.scale_y

        raw_rect = pymupdf.Rect(x0, y0, x1, y1)
        safe_rect = raw_rect.intersect(self.current_page.rect)
        return safe_rect

    def highlight_text(self):
        target_rect = self.get_pdf_rect_from_ui()
        if not target_rect or target_rect.is_empty:
            QMessageBox.warning(self, "Ошибка", "Сначала выделите область с текстом мышкой!")
            return

        words = self.current_page.get_text("words")
        highlight_added = False

        for w in words:
            word_rect = pymupdf.Rect(w[0], w[1], w[2], w[3])
            if word_rect.intersects(target_rect):
                self.current_page.add_highlight_annot(word_rect)
                highlight_added = True

        if highlight_added:
            self.render_page()
        else:
            QMessageBox.information(self, "Пусто", "В выделенной области не найден текст.")

    def redact_text(self):
        target_rect = self.get_pdf_rect_from_ui()
        if not target_rect or target_rect.is_empty:
            QMessageBox.warning(self, "Ошибка", "Сначала выделите текст для закрашивания!")
            return

        self.current_page.add_redact_annot(target_rect, fill=(0, 0, 0))
        self.current_page.apply_redactions()
        self.render_page()

    def crop_pdf(self):
        target_rect = self.get_pdf_rect_from_ui()
        if not target_rect or target_rect.is_empty:
            QMessageBox.warning(self, "Ошибка", "Сначала выделите область мышкой!")
            return

        # Применяем кадрирование только к текущей странице
        self.current_page.set_cropbox(target_rect)
        self.save_pdf(default_name="cropped.pdf")

    def save_pdf(self, default_name="modified.pdf"):
        save_path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить как...", default_name, "PDF Files (*.pdf)"
        )
        if save_path:
            if not save_path.lower().endswith('.pdf'):
                save_path += '.pdf'
            self.doc.save(save_path)
            QMessageBox.information(self, "Успех", f"Файл сохранен:\n{save_path}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PDFApp()
    window.show()
    sys.exit(app.exec())
