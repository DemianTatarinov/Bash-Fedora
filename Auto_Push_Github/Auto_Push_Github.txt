#!/usr/bin/env python3
import sys
import os
import subprocess
import tempfile
import shutil
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QComboBox, QPushButton,
                             QTextEdit, QProgressBar, QStackedWidget, QMessageBox,
                             QListWidget, QListWidgetItem)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont

class GitWorker(QThread):
    progress_signal = pyqtSignal(int, str)
    status_signal = pyqtSignal(str)
    repos_loaded_signal = pyqtSignal(list)
    repo_cloned_signal = pyqtSignal(str)
    duplicates_signal = pyqtSignal(list)
    need_readme_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, source_dir, script_path):
        super().__init__()
        self.source_dir = source_dir
        self.script_path = script_path
        self.action = "load_repos"
        self.chosen_repo = ""
        self.target_repo_path = ""
        self.temp_dir = ""
        self.files_to_add = []
        self.readme_text = ""
        self.default_branch = "main"
        self.create_subfolder = True

    def run(self):
        try:
            if self.action == "load_repos":
                self.load_repos()
            elif self.action == "clone_repo":
                self.clone_repo()
            elif self.action == "analyze_files":
                self.analyze_files()
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

    def clone_repo(self):
        self.progress_signal.emit(10, f"Клонирование {self.chosen_repo}...")
        self.temp_dir = tempfile.mkdtemp(prefix="git-push-py-")

        clone_res = subprocess.run(["gh", "repo", "clone", self.chosen_repo, self.temp_dir, "--", "--depth", "1", "--quiet"], capture_output=True)
        if clone_res.returncode != 0:
            raise Exception("Не удалось клонировать репозиторий.")

        branch_res = subprocess.run(["git", "symbolic-ref", "--short", "refs/remotes/origin/HEAD"], cwd=self.temp_dir, capture_output=True, text=True)
        if branch_res.returncode == 0:
            self.default_branch = branch_res.stdout.strip().replace("origin/", "")
        else:
            self.default_branch = "main"

        self.repo_cloned_signal.emit(self.temp_dir)

    def analyze_files(self):
        self.progress_signal.emit(40, "Поиск файлов в рабочей директории...")
        all_files = []
        for root, dirs, files in os.walk(self.source_dir):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ('venv', 'env', '__pycache__')]
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

        current_folder_name = os.path.basename(os.path.abspath(self.source_dir))

        copied_relative_paths = []
        for src_file in all_files:
            rel_path = os.path.relpath(src_file, self.source_dir)

            # Собираем финальный путь внутри репозитория
            path_parts = []
            if self.target_repo_path and self.target_repo_path != ".":
                path_parts.append(self.target_repo_path)
            if self.create_subfolder:
                path_parts.append(current_folder_name)
            path_parts.append(rel_path)

            git_rel_path = os.path.join(*path_parts).replace('\\', '/')
            dest_path = os.path.join(self.temp_dir, git_rel_path)

            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            shutil.copy2(src_file, dest_path)
            copied_relative_paths.append(git_rel_path)

        self.files_to_add = []
        duplicates = []

        for rel_path in copied_relative_paths:
            show_check = subprocess.run(["git", "show", f"HEAD:{rel_path}"], cwd=self.temp_dir, capture_output=True)
            if show_check.returncode == 0:
                diff_check = subprocess.run(["git", "diff", "--quiet", f"HEAD:{rel_path}", "--", rel_path], cwd=self.temp_dir)
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

        readme_path = os.path.join(self.temp_dir, "README.md")
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(self.readme_text)

        subprocess.run(["git", "add", "README.md"], cwd=self.temp_dir)
        for file in self.files_to_add:
            subprocess.run(["git", "add", file], cwd=self.temp_dir)

        self.progress_signal.emit(90, "Создание коммита...")
        commit_msg = f"Авто-пуш: добавлены/обновлены файлы проекта {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        subprocess.run(["git", "commit", "-m", commit_msg], cwd=self.temp_dir, capture_output=True)

        self.progress_signal.emit(95, "Авторизация и безопасная отправка...")

        token_res = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True)
        token = token_res.stdout.strip()

        if not token:
            raise Exception("Не удалось получить токен авторизации из GitHub CLI!")

        auth_url = f"https://oauth2:{token}@github.com/{self.chosen_repo}.git"
        subprocess.run(["git", "remote", "set-url", "origin", auth_url], cwd=self.temp_dir)

        subprocess.run(["git", "config", "user.name", "DemianTatarinov"], cwd=self.temp_dir)
        subprocess.run(["git", "config", "user.email", "demiantatarynau@icloud.com"], cwd=self.temp_dir)

        subprocess.run(["git", "pull", "origin", self.default_branch, "--rebase=false", "-X", "ours", "--quiet"], cwd=self.temp_dir, capture_output=True)

        push_res = subprocess.run(["git", "push", "origin", self.default_branch], cwd=self.temp_dir, capture_output=True, text=True)

        if push_res.returncode != 0:
            error_details = push_res.stderr if push_res.stderr else "Неизвестная ошибка Git"
            raise Exception(f"GitHub отклонил отправку:\n{error_details}")

        self.progress_signal.emit(100, "Всё готово!")
        self.finished_signal.emit(True, f"Изменения успешно отправлены в {self.chosen_repo}!")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GitHub Auto-Push Manager")
        self.resize(750, 550)

        self.script_path = os.path.realpath(__file__)
        self.source_dir = os.path.dirname(self.script_path)
        self.current_browse_path = ""

        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)

        self.init_repo_selection_page()
        self.init_loading_page()
        self.init_folder_browser_page()
        self.init_readme_page()

        self.worker = GitWorker(self.source_dir, self.script_path)
        self.worker.status_signal.connect(self.update_status_label)
        self.worker.repos_loaded_signal.connect(self.on_repos_loaded)
        self.worker.repo_cloned_signal.connect(self.on_repo_cloned)
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

        self.select_btn = QPushButton("Просмотр папок репозитория")
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

    def init_folder_browser_page(self):
        page = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(10)

        self.path_label = QLabel("Текущая папка: /")
        self.path_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(self.path_label)

        controls_layout = QHBoxLayout()

        self.cancel_browse_btn = QPushButton("Отмена")
        self.cancel_browse_btn.setFont(QFont("Arial", 11))
        self.cancel_browse_btn.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(0))
        controls_layout.addWidget(self.cancel_browse_btn)

        self.up_btn = QPushButton("⬅ На уровень выше")
        self.up_btn.setFont(QFont("Arial", 11))
        self.up_btn.clicked.connect(self.go_up_level)
        self.up_btn.setEnabled(False)
        controls_layout.addWidget(self.up_btn)

        controls_layout.addStretch()
        layout.addLayout(controls_layout)

        self.folder_list = QListWidget()
        self.folder_list.setFont(QFont("Arial", 11))
        self.folder_list.itemDoubleClicked.connect(self.on_folder_double_clicked)
        layout.addWidget(self.folder_list)

        self.select_folder_btn = QPushButton("Выбрать эту папку для деплоя")
        self.select_folder_btn.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.select_folder_btn.setMinimumHeight(45)
        self.select_folder_btn.clicked.connect(self.confirm_folder_selection)
        layout.addWidget(self.select_folder_btn)

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
        self.repo_combo.clear()
        self.repo_combo.addItems(repos)
        self.select_btn.setEnabled(True)

    def start_sync(self):
        self.worker.chosen_repo = self.repo_combo.currentText()
        self.worker.action = "clone_repo"
        self.stacked_widget.setCurrentIndex(1)
        self.worker.start()

    def on_repo_cloned(self, temp_dir):
        self.current_browse_path = temp_dir
        self.update_folder_list()
        self.stacked_widget.setCurrentIndex(2)

    def update_folder_list(self):
        self.folder_list.clear()

        is_root = os.path.normcase(os.path.abspath(self.current_browse_path)) == os.path.normcase(os.path.abspath(self.worker.temp_dir))

        if is_root:
            self.up_btn.setEnabled(False)
            rel_display = "/"
        else:
            self.up_btn.setEnabled(True)
            rel = os.path.relpath(self.current_browse_path, self.worker.temp_dir)
            rel_display = f"/{rel.replace(os.sep, '/')}"

        self.path_label.setText(f"Текущая папка: {rel_display}")
        self.select_folder_btn.setText(f"Выбрать папку: {rel_display}")

        try:
            items = os.listdir(self.current_browse_path)
        except Exception:
            items = []

        folders = []
        files = []

        for item in items:
            if item == '.git':
                continue
            item_path = os.path.join(self.current_browse_path, item)
            if os.path.isdir(item_path):
                folders.append(item)
            else:
                files.append(item)

        folders.sort()
        files.sort()

        for folder in folders:
            it = QListWidgetItem(f"📁 {folder}")
            it.setData(Qt.ItemDataRole.UserRole, "folder")
            self.folder_list.addItem(it)

        for file in files:
            it = QListWidgetItem(f"📄 {file}")
            it.setData(Qt.ItemDataRole.UserRole, "file")
            self.folder_list.addItem(it)

    def on_folder_double_clicked(self, item):
        item_type = item.data(Qt.ItemDataRole.UserRole)
        if item_type == "folder":
            folder_name = item.text().replace("📁 ", "")
            self.current_browse_path = os.path.join(self.current_browse_path, folder_name)
            self.update_folder_list()

    def go_up_level(self):
        self.current_browse_path = os.path.dirname(self.current_browse_path)
        self.update_folder_list()

    def confirm_folder_selection(self):
        rel_path = os.path.relpath(self.current_browse_path, self.worker.temp_dir)
        if rel_path == ".":
            rel_path = ""
        else:
            rel_path = rel_path.replace(os.sep, '/')

        self.worker.target_repo_path = rel_path
        current_folder_name = os.path.basename(os.path.abspath(self.source_dir))

        reply = QMessageBox.question(
            self,
            "Структура репозитория",
            f"Хотите создать отдельную папку '{current_folder_name}' внутри выбранного пути ({rel_path or '/'})?\n\n"
            "• Нажмите 'Да', чтобы изолировать файлы проекта в этой папке.\n"
            "• Нажмите 'Нет', чтобы выгрузить файлы прямо в текущую папку.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )

        self.worker.create_subfolder = (reply == QMessageBox.StandardButton.Yes)
        self.worker.action = "analyze_files"
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
        self.stacked_widget.setCurrentIndex(3)

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
            try:
                shutil.rmtree(self.worker.temp_dir)
            except Exception:
                pass
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
