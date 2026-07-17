#!/usr/bin/env python3
import sys
import os
import subprocess
import tempfile
import shutil
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QComboBox, QPushButton,
                             QTextEdit, QProgressBar, QStackedWidget, QMessageBox)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont

class GitWorker(QThread):
    progress_signal = pyqtSignal(int, str)
    status_signal = pyqtSignal(str)
    repos_loaded_signal = pyqtSignal(list)
    duplicates_signal = pyqtSignal(list)
    need_readme_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, source_dir, script_path):
        super().__init__()
        self.source_dir = source_dir
        self.script_path = script_path
        self.action = "load_repos"
        self.chosen_repo = ""
        self.temp_dir = ""
        self.files_to_add = []
        self.readme_text = ""

    def run(self):
        try:
            if self.action == "load_repos":
                self.load_repos()
            elif self.action == "clone_and_analyze":
                self.clone_and_analyze()
            elif self.action == "final_push":
                self.final_push()
        except Exception as e:
            self.finished_signal.emit(False, str(e))

    def load_repos(self):
        self.status_signal.emit("Получение списка репозиториев...")
        if shutil.which("gh") is None:
            raise Exception("GitHub CLI (gh) не установлен в системе!")

        auth_check = subprocess.run(["gh", "auth", "status"], capture_output=True, text=True)
        if auth_check.returncode != 0:
            raise Exception("Вы не авторизованы в GitHub CLI. Запустите в терминале 'gh auth login'.")

        res = subprocess.run(["gh", "repo", "list", "--limit", "100", "--visibility", "public", "--json", "nameWithOwner", "-q", ".[] | .nameWithOwner"], capture_output=True, text=True)
        repos = [r.strip() for r in res.stdout.strip().split('\n') if r.strip()]
        self.repos_loaded_signal.emit(repos)

    def clone_and_analyze(self):
        self.progress_signal.emit(10, f"Клонирование {self.chosen_repo}...")
        self.temp_dir = tempfile.mkdtemp(prefix="git-push-py-")

        # Клонируем через gh
        clone_res = subprocess.run(["gh", "repo", "clone", self.chosen_repo, self.temp_dir, "--", "--depth", "1", "--quiet"], capture_output=True)
        if clone_res.returncode != 0:
            raise Exception("Не удалось клонировать репозиторий.")

        self.progress_signal.emit(40, "Поиск файлов в рабочей директории...")
        all_files = []
        for root, dirs, files in os.walk(self.source_dir):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for file in files:
                if file.startswith('.'):
                    continue
                abs_path = os.path.join(root, file)
                if abs_path == self.script_path:
                    continue
                all_files.append(abs_path)

        if not all_files:
            raise Exception("В папке со скриптом нет файлов для отправки!")

        self.progress_signal.emit(60, "Анализ файлов на дубликаты...")

        copied_relative_paths = []
        for src_file in all_files:
            rel_path = os.path.relpath(src_file, self.source_dir)
            dest_path = os.path.join(self.temp_dir, rel_path)
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            shutil.copy2(src_file, dest_path)
            copied_relative_paths.append(rel_path)

        self.files_to_add = []
        duplicates = []

        os.chdir(self.temp_dir)
        for rel_path in copied_relative_paths:
            show_check = subprocess.run(["git", "show", f"HEAD:{rel_path}"], capture_output=True)
            if show_check.returncode == 0:
                diff_check = subprocess.run(["git", "diff", "--quiet", f"HEAD:{rel_path}", "--", rel_path])
                if diff_check.returncode == 0:
                    duplicates.append(rel_path)
                else:
                    self.files_to_add.append(rel_path)
            else:
                self.files_to_add.append(rel_path)

        if duplicates:
            self.duplicates_signal.emit(duplicates)

        if not self.files_to_add:
            self.finished_signal.emit(True, "Все файлы идентичны версиям на GitHub. Отправка не требуется!")
            return

        self.progress_signal.emit(80, "Загрузка README.md...")
        readme_path = os.path.join(self.temp_dir, "README.md")
        current_readme = f"# {self.chosen_repo}\n\nОписание проекта."
        if os.path.exists(readme_path):
            with open(readme_path, "r", encoding="utf-8") as f:
                current_readme = f.read()

        self.need_readme_signal.emit(current_readme)

    def final_push(self):
        self.progress_signal.emit(85, "Сохранение README.md и индексация...")
        os.chdir(self.temp_dir)

        with open("README.md", "w", encoding="utf-8") as f:
            f.write(self.readme_text)

        subprocess.run(["git", "add", "README.md"])
        for file in self.files_to_add:
            subprocess.run(["git", "add", file])

        self.progress_signal.emit(90, "Создание коммита...")
        commit_msg = f"Авто-пуш: добавлены/обновлены файлы проекта {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        subprocess.run(["git", "commit", "-m", commit_msg], capture_output=True)

        self.progress_signal.emit(95, "Синхронизация и отправка через GitHub CLI...")

        # Получаем токен авторизации напрямую из gh cli
        token_res = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True)
        token = token_res.stdout.strip()

        if not token:
            raise Exception("Не удалось получить токен авторизации из GitHub CLI!")

        # Перезаписываем URL удаленного репозитория, внедряя в него токен авторизации.
        # Это гарантирует, что Git сможет запушить файлы без каких-либо внешних хелперов.
        auth_url = f"https://oauth2:{token}@github.com/{self.chosen_repo}.git"
        subprocess.run(["git", "remote", "set-url", "origin", auth_url])

        # Подтягиваем изменения
        subprocess.run(["git", "pull", "origin", "main", "--allow-unrelated-histories", "--no-rebase", "-X", "ours", "--quiet"], capture_output=True)

        # Пушим напрямую с авторизованным URL
        push_res = subprocess.run(["git", "push", "origin", "main"], capture_output=True)
        if push_res.returncode != 0:
            self.status_signal.emit("Обычный пуш отклонен. Пробиваем через Force...")
            force_res = subprocess.run(["git", "push", "origin", "main", "--force"], capture_output=True)
            if force_res.returncode != 0:
                raise Exception("Ошибка отправки! Сервер отклонил Force Push.")

        self.progress_signal.emit(100, "Всё готово!")
        self.finished_signal.emit(True, f"Изменения успешно отправлены в {self.chosen_repo}!")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GitHub Auto-Push Manager")
        self.resize(700, 500)

        self.script_path = os.path.realpath(__file__)
        self.source_dir = os.path.dirname(self.script_path)

        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)

        self.init_repo_selection_page()
        self.init_loading_page()
        self.init_readme_page()

        self.worker = GitWorker(self.source_dir, self.script_path)
        self.worker.status_signal.connect(self.update_status_label)
        self.worker.repos_loaded_signal.connect(self.on_repos_loaded)
        self.worker.progress_signal.connect(self.update_progress)
        self.worker.duplicates_signal.connect(self.show_duplicates_dialog)
        self.worker.need_readme_signal.connect(self.open_readme_editor)
        self.worker.finished_signal.connect(self.on_finished)

        self.worker.start()

    def init_repo_selection_page(self):
        page = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(15)

        title = QLabel("Выберите репозиторий для отправки:")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        layout.addWidget(title)

        self.repo_combo = QComboBox()
        self.repo_combo.setFont(QFont("Arial", 11))
        self.repo_combo.setMinimumHeight(40)
        layout.addWidget(self.repo_combo)

        self.select_btn = QPushButton("Начать синхронизацию")
        self.select_btn.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.select_btn.setMinimumHeight(45)
        self.select_btn.setEnabled(False)
        self.select_btn.clicked.connect(self.start_sync)
        layout.addWidget(self.select_btn)

        page.setLayout(layout)
        self.stacked_widget.addWidget(page)

    def init_loading_page(self):
        page = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.loading_label = QLabel("Загрузка данных...")
        self.loading_label.setFont(QFont("Arial", 13))
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.loading_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setMinimumWidth(500)
        self.progress_bar.setMinimumHeight(30)
        self.progress_bar.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        layout.addWidget(self.progress_bar)

        page.setLayout(layout)
        self.stacked_widget.addWidget(page)

    def init_readme_page(self):
        page = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(10)

        title = QLabel("Редактирование файла README.md:")
        title.setFont(QFont("Arial", 13, QFont.Weight.Bold))
        layout.addWidget(title)

        self.readme_edit = QTextEdit()
        self.readme_edit.setFont(QFont("Monospace", 11))
        layout.addWidget(self.readme_edit)

        btn_layout = QHBoxLayout()
        cancel_btn = QPushButton("Отменить пуш")
        cancel_btn.setFont(QFont("Arial", 11))
        cancel_btn.setMinimumHeight(40)
        cancel_btn.clicked.connect(self.close)

        self.push_btn = QPushButton("Сохранить и отправить на GitHub 🚀")
        self.push_btn.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.push_btn.setMinimumHeight(40)
        self.push_btn.clicked.connect(self.submit_readme)

        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(self.push_btn)
        layout.addLayout(btn_layout)

        page.setLayout(layout)
        self.stacked_widget.addWidget(page)

    def update_status_label(self, text):
        self.loading_label.setText(text)

    def on_repos_loaded(self, repos):
        self.repo_combo.addItems(repos)
        self.select_btn.setEnabled(True)

    def start_sync(self):
        self.worker.chosen_repo = self.repo_combo.currentText()
        self.worker.action = "clone_and_analyze"
        self.stacked_widget.setCurrentIndex(1)
        self.worker.start()

    def update_progress(self, val, text):
        self.progress_bar.setValue(val)
        self.loading_label.setText(text)

    def show_duplicates_dialog(self, duplicates):
        dup_list = "\n".join([f"• {d}" for d in duplicates])
        QMessageBox.information(self, "Обнаружены дубликаты",
                                f"Следующие файлы уже есть на GitHub и не изменились:\n\n{dup_list}\n\nОни будут пропущены.")

    def open_readme_editor(self, text):
        self.readme_edit.setPlainText(text)
        self.stacked_widget.setCurrentIndex(2)

    def submit_readme(self):
        self.worker.readme_text = self.readme_edit.toPlainText()
        self.worker.action = "final_push"
        self.stacked_widget.setCurrentIndex(1)
        self.worker.start()

    def on_finished(self, success, message):
        if success:
            QMessageBox.information(self, "Успех", message)
            self.close()
        else:
            QMessageBox.critical(self, "Ошибка", f"Произошла ошибка:\n\n{message}")
            self.stacked_widget.setCurrentIndex(0)

    def closeEvent(self, event):
        if self.worker.temp_dir and os.path.exists(self.worker.temp_dir):
            shutil.rmtree(self.worker.temp_dir)
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
