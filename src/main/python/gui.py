from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QComboBox, QTextEdit, QLineEdit, QLabel, QMessageBox, QProgressBar,
    QSplitter, QInputDialog, QStatusBar, QToolButton, QFrame, QDialog,
    QFormLayout, QMenuBar, QMenu, QFileDialog, QCheckBox, QTabWidget
)
from PyQt6.QtGui import (
    QIcon, QKeySequence, QTextCharFormat, QColor, QPalette, QAction
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, pyqtSlot
import numpy as np
from openai import OpenAI
from pathlib import Path
import threading
import queue
import time
import os

from config import Config
from audio_manager import AudioManager

# Define color scheme
COLORS = {
    'primary': '#2196F3',    # Blue
    'secondary': '#4CAF50',  # Green
    'accent': '#FF9800',     # Orange
    'error': '#F44336',      # Red
    'background': '#F5F5F5', # Light Gray
    'text': '#212121',       # Dark Gray
    'disabled': '#9E9E9E'    # Medium Gray
}

class TranscribeWorker(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, api_key, audio_path):
        super().__init__()
        self.api_key = api_key
        self.audio_path = audio_path

    def run(self):
        try:
            if not Path(self.audio_path).exists():
                raise FileNotFoundError("Audio file not found")
                
            if not self.api_key:
                raise ValueError("OpenAI API key not set")

            client = OpenAI(api_key=self.api_key)
            
            with open(self.audio_path, 'rb') as audio_file:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file
                )
            self.finished.emit(transcript.text)
        except FileNotFoundError as e:
            self.error.emit(f"Audio file error: {str(e)}")
        except Exception as e:
            if "authentication" in str(e).lower():
                self.error.emit("Invalid OpenAI API key")
            elif "rate limit" in str(e).lower():
                self.error.emit("OpenAI API rate limit exceeded")
            else:
                self.error.emit(f"Transcription error: {str(e)}")

class FormatWorker(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, api_key, text, temperature):
        super().__init__()
        self.api_key = api_key
        self.text = text
        self.temperature = temperature

    def run(self):
        try:
            client = OpenAI(api_key=self.api_key)
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                temperature=self.temperature,
                messages=[
                    {"role": "system", "content": """Your task is to edit text captured using speech to text and format it in two parts:
1. A title that captures the main essence of the note
2. The formatted content of the note

Your response must follow this exact format:
Title: [Your generated title here]
[Blank line]
[Your formatted content here]

For the content:
- Edit lightly for clarity
- Remove speech artifacts (like 'um')
- Remove any meta-instructions (like 'take that out of the note')
- Ensure all important thoughts and details are preserved
- Use proper paragraphs and formatting"""},
                    {"role": "user", "content": self.text}
                ]
            )
            self.finished.emit(response.choices[0].message.content)
        except Exception as e:
            self.error.emit(str(e))

class SettingsDialog(QDialog):
    def __init__(self, config, audio_manager, parent=None):
        super().__init__(parent)
        self.config = config
        self.audio_manager = audio_manager
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle("Settings")
        layout = QFormLayout(self)

        # API Key
        self.api_key_input = QLineEdit(self.config.get("openai_api_key", ""))
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.show_api_key = QPushButton("Show")
        self.show_api_key.setCheckable(True)
        self.show_api_key.clicked.connect(self.toggle_api_key_visibility)
        
        api_key_layout = QHBoxLayout()
        api_key_layout.addWidget(self.api_key_input)
        api_key_layout.addWidget(self.show_api_key)
        layout.addRow("OpenAI API Key:", api_key_layout)
        
        # Default Microphone
        self.mic_combo = QComboBox()
        self.populate_audio_devices()
        layout.addRow("Default Microphone:", self.mic_combo)

        # Default Export Format
        self.format_combo = QComboBox()
        self.format_combo.addItems(["Markdown", "PDF", "DocX", "Text"])
        current_format = self.config.get('default_export_format', 'Markdown')
        self.format_combo.setCurrentText(current_format)
        layout.addRow("Default Export Format:", self.format_combo)

        # Default Download Format
        self.download_format_combo = QComboBox()
        self.download_format_combo.addItems(["Markdown", "PDF", "DOCX"])
        current_format = self.config.get("default_download_format", "Markdown")
        self.download_format_combo.setCurrentText(current_format)
        layout.addRow("Default Download Format:", self.download_format_combo)

        # Temperature Setting
        self.temp_combo = QComboBox()
        self.temp_combo.addItems(['0.0', '0.3', '0.5', '0.7', '1.0'])
        current_temp = str(self.config.get('gpt_temperature', 0.3))
        self.temp_combo.setCurrentText(current_temp)
        layout.addRow("GPT Temperature:", self.temp_combo)

        # Download Path
        self.download_path_input = QLineEdit(self.config.get("download_path", ""))
        self.browse_button = QPushButton("Browse")
        self.browse_button.clicked.connect(self.browse_download_path)
        download_path_layout = QHBoxLayout()
        download_path_layout.addWidget(self.download_path_input)
        download_path_layout.addWidget(self.browse_button)
        layout.addRow("Download Path:", download_path_layout)

        # Include Raw Text
        self.include_raw_checkbox = QCheckBox("Include Original Text")
        self.include_raw_checkbox.setChecked(self.config.get("include_raw_text", False))
        layout.addRow("Include Original Text:", self.include_raw_checkbox)

        # Buttons
        button_box = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_settings)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_box.addWidget(save_btn)
        button_box.addWidget(cancel_btn)
        layout.addRow("", button_box)

    def populate_audio_devices(self):
        devices = self.audio_manager.get_available_devices()
        self.mic_combo.clear()
        for device in devices:
            self.mic_combo.addItem(device['name'], device['index'])
        
        preferred_device = self.config.get_preferred_audio_device()
        if preferred_device is not None:
            index = self.mic_combo.findData(preferred_device)
            if index >= 0:
                self.mic_combo.setCurrentIndex(index)

    def toggle_api_key_visibility(self, checked):
        self.api_key_input.setEchoMode(
            QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
        )

    def browse_download_path(self):
        path = QFileDialog.getExistingDirectory(self, "Select Download Directory")
        if path:
            self.download_path_input.setText(path)

    def save_settings(self):
        # Save API Key
        api_key = self.api_key_input.text().strip()
        if api_key:
            self.config.api_key = api_key

        # Save preferred audio device
        device_index = self.mic_combo.currentData()
        self.config.set_preferred_audio_device(device_index)

        # Save default export format
        self.config.set('default_export_format', self.format_combo.currentText())

        # Save default download format
        self.config.set("default_download_format", self.download_format_combo.currentText())

        # Save temperature
        self.config.set('gpt_temperature', float(self.temp_combo.currentText()))

        # Save download path
        self.config.set('download_path', self.download_path_input.text())

        # Save include raw text setting
        self.config.set('include_raw_text', self.include_raw_checkbox.isChecked())

        self.accept()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config = Config()
        self.audio_manager = AudioManager()
        self.recording_start_time = 0
        self.recording_timer = QTimer()
        self.recording_timer.timeout.connect(self.update_recording_time)
        self.recording_timer.setInterval(1000)  # Update every second
        self.setup_ui()
        self.setup_auto_save()
        self.apply_stylesheet()
        self.check_api_key()

    def setup_ui(self):
        self.setWindowTitle("Thought Pad v1 - Notepad and formatting tool for dictated text")
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Create tab widget
        tab_widget = QTabWidget()
        main_tab = QWidget()
        info_tab = QWidget()
        settings_tab = QWidget()
        tab_widget.addTab(main_tab, "Main")
        tab_widget.addTab(info_tab, "Info")
        tab_widget.addTab(settings_tab, "Settings")

        # Setup main tab
        main_layout_tab = QVBoxLayout(main_tab)
        
        # Audio device selection
        device_layout = QHBoxLayout()
        self.device_combo = QComboBox()
        self.populate_audio_devices()
        device_layout.addWidget(self.device_combo)
        main_layout_tab.addLayout(device_layout)

        # Recording controls
        controls_layout = QHBoxLayout()
        self.record_button = QPushButton("Record")
        self.pause_button = QPushButton("Pause")
        self.stop_button = QPushButton("Stop")
        self.reset_button = QPushButton("Reset")
        
        self.record_button.setStyleSheet(f"background-color: {COLORS['primary']}; color: white;")
        self.pause_button.setStyleSheet(f"background-color: {COLORS['accent']}; color: white;")
        self.stop_button.setStyleSheet(f"background-color: {COLORS['secondary']}; color: white;")
        self.reset_button.setStyleSheet(f"background-color: {COLORS['error']}; color: white;")
        
        # Add recording time label
        self.recording_time_label = QLabel("00:00")
        self.recording_time_label.setStyleSheet("""
            QLabel {
                color: #666666;
                font-size: 14px;
                padding: 5px;
                min-width: 60px;
                text-align: right;
            }
        """)
        
        controls_layout.addWidget(self.record_button)
        controls_layout.addWidget(self.pause_button)
        controls_layout.addWidget(self.stop_button)
        controls_layout.addWidget(self.reset_button)
        controls_layout.addStretch()  # This pushes the time label to the right
        controls_layout.addWidget(self.recording_time_label)
        main_layout_tab.addLayout(controls_layout)

        # Title display
        title_layout = QHBoxLayout()
        title_label = QLabel("Title:")
        self.title_display = QLineEdit()
        self.title_display.setReadOnly(True)
        title_layout.addWidget(title_label)
        title_layout.addWidget(self.title_display)
        main_layout_tab.addLayout(title_layout)

        # Text areas
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Raw text container
        raw_container = QWidget()
        raw_layout = QVBoxLayout(raw_container)
        raw_label = QLabel("Raw Text:")
        self.raw_text = QTextEdit()
        raw_layout.addWidget(raw_label)
        raw_layout.addWidget(self.raw_text)
        
        # Format button between text areas
        format_container = QWidget()
        format_layout = QHBoxLayout(format_container)
        format_layout.addStretch()
        self.format_button = QPushButton("Format Text")
        self.format_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:disabled {
                background-color: #BDBDBD;
            }
        """)
        self.format_button.setToolTip("Format Text (Ctrl+F)")
        self.format_button.setShortcut(QKeySequence("Ctrl+F"))
        format_layout.addWidget(self.format_button)
        format_layout.addStretch()
        
        # Formatted text container
        formatted_container = QWidget()
        formatted_layout = QVBoxLayout(formatted_container)
        formatted_label = QLabel("Formatted Text:")
        self.formatted_text = QTextEdit()
        formatted_layout.addWidget(formatted_label)
        formatted_layout.addWidget(self.formatted_text)
        
        splitter.addWidget(raw_container)
        splitter.addWidget(format_container)
        splitter.addWidget(formatted_container)
        main_layout_tab.addWidget(splitter)

        # Word count and download
        bottom_layout = QHBoxLayout()
        self.word_count_label = QLabel("Words: 0")
        self.download_button = QPushButton("Download")
        self.download_button.setStyleSheet(f"background-color: {COLORS['primary']}; color: white;")
        
        bottom_layout.addWidget(self.word_count_label)
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.download_button)
        main_layout_tab.addLayout(bottom_layout)

        # Setup info tab
        info_layout = QVBoxLayout(info_tab)
        
        instructions = """
# ThoughtPad Instructions

1. Select your microphone from the dropdown menu
2. Click 'Record' to start recording your voice note
3. Use 'Pause' to temporarily pause recording
4. Click 'Stop' when finished recording
5. Wait for the transcription and formatting to complete
6. Review the raw and formatted text
7. Click 'Download' to save your note

The app will automatically:
- Transcribe your voice recording using OpenAI Whisper
- Format the text for clarity using GPT
- Generate an appropriate title
- Save the file using the generated title

# Credits

ThoughtPad v1 was designed by Claude Sonnet 3.5 and [Daniel Rosehill](https://danielrosehill.com)

This tool uses OpenAI's Whisper and GPT models for transcription and text formatting.
"""
        info_text = QTextEdit()
        info_text.setMarkdown(instructions)
        info_text.setReadOnly(True)
        info_layout.addWidget(info_text)

        # Setup settings tab
        settings_layout = QFormLayout(settings_tab)
        
        # API Key
        api_key_layout = QHBoxLayout()
        api_key_label = QLabel("OpenAI API Key:")
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.show_api_key = QPushButton("Show")
        self.show_api_key.setCheckable(True)
        self.show_api_key.clicked.connect(self.toggle_api_key_visibility)
        api_key_layout.addWidget(self.api_key_input)
        api_key_layout.addWidget(self.show_api_key)
        settings_layout.addRow("OpenAI API Key:", api_key_layout)

        # Temperature Setting
        self.temp_combo = QComboBox()
        self.temp_combo.addItems(['0.0', '0.3', '0.5', '0.7', '1.0'])
        current_temp = str(self.config.get('gpt_temperature', 0.3))
        self.temp_combo.setCurrentText(current_temp)
        settings_layout.addRow("GPT Temperature:", self.temp_combo)

        # Download Path
        self.download_path_input = QLineEdit(self.config.get("download_path", ""))
        self.browse_button = QPushButton("Browse")
        self.browse_button.clicked.connect(self.browse_download_path)
        download_path_layout = QHBoxLayout()
        download_path_layout.addWidget(self.download_path_input)
        download_path_layout.addWidget(self.browse_button)
        settings_layout.addRow("Download Path:", download_path_layout)

        # Save Settings Button
        self.save_settings_button = QPushButton("Save Settings")
        self.save_settings_button.clicked.connect(self.save_settings)
        self.save_settings_button.setStyleSheet(f"background-color: {COLORS['primary']}; color: white;")
        settings_layout.addRow("", self.save_settings_button)

        main_layout.addWidget(tab_widget)

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        self.connect_signals()
        self.reset_all()

    def toggle_api_key_visibility(self, checked):
        self.api_key_input.setEchoMode(
            QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
        )

    def browse_download_path(self):
        path = QFileDialog.getExistingDirectory(self, "Select Download Directory")
        if path:
            self.download_path_input.setText(path)

    def save_settings(self):
        # Save API Key
        api_key = self.api_key_input.text().strip()
        if api_key:
            self.config.api_key = api_key

        # Save temperature
        self.config.set('gpt_temperature', float(self.temp_combo.currentText()))

        # Save download path
        download_path = self.download_path_input.text().strip()
        if download_path:
            self.config.set("download_path", download_path)

        self.update_status("Settings saved successfully", "green")

    def setup_menu(self):
        menubar = self.menuBar()
        
        # File Menu
        file_menu = menubar.addMenu('File')
        
        settings_action = QAction('Settings', self)
        settings_action.setShortcut('Ctrl+,')
        settings_action.triggered.connect(self.show_settings)
        file_menu.addAction(settings_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction('Exit', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

    def show_settings(self):
        dialog = SettingsDialog(self.config, self.audio_manager, self)
        if dialog.exec_() == QDialog.Accepted:
            # Refresh UI based on new settings
            self.populate_audio_devices()
            self.format_combo.setCurrentText(self.config.get('default_export_format', 'Markdown'))
            self.include_raw_checkbox.setChecked(self.config.get("include_raw_text", False))

    def connect_signals(self):
        self.record_button.clicked.connect(self.toggle_recording)
        self.pause_button.clicked.connect(self.toggle_pause)
        self.stop_button.clicked.connect(self.stop_recording)
        self.reset_button.clicked.connect(self.reset_all)
        self.format_button.clicked.connect(self.format_text)
        self.download_button.clicked.connect(self.download_text)
        self.device_combo.currentIndexChanged.connect(self.change_audio_device)

    def populate_audio_devices(self):
        devices = self.audio_manager.get_available_devices()
        self.device_combo.clear()
        for device in devices:
            self.device_combo.addItem(device['name'], device['index'])
        
        # Set preferred device if configured
        preferred_device = self.config.get_preferred_audio_device()
        if preferred_device is not None:
            index = self.device_combo.findData(preferred_device)
            if index >= 0:
                self.device_combo.setCurrentIndex(index)

    def change_audio_device(self, index):
        device_index = self.device_combo.currentData()
        if device_index is not None:
            self.audio_manager.set_device(device_index)
            self.config.set_preferred_audio_device(device_index)

    def toggle_recording(self):
        if not self.audio_manager.recording:
            self.audio_manager.start_recording()
            self.record_button.setText("Recording...")
            self.pause_button.setEnabled(True)
            self.stop_button.setEnabled(True)
            self.recording_start_time = time.time()
            self.recording_timer.start()
            self.update_status("Recording...", color=COLORS['error'])
        else:
            self.audio_manager.pause_recording()
            self.record_button.setText("Resume")
            self.recording_timer.stop()
            self.update_status("Paused", color=COLORS['accent'])

    def toggle_pause(self):
        if self.audio_manager.paused:
            self.audio_manager.resume_recording()
            self.recording_timer.start()
            self.update_status("Recording...", color=COLORS['error'])
        else:
            self.audio_manager.pause_recording()
            self.recording_timer.stop()
            self.update_status("Paused", color=COLORS['accent'])

    def stop_recording(self):
        self.audio_manager.stop_recording()
        self.record_button.setText("Record")
        self.pause_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        self.recording_time_label.setText("00:00")
        self.recording_timer.stop()
        self.transcribe_audio()

    def reset_all(self):
        """Reset all fields and state to initial values."""
        # Stop any ongoing recording
        if self.audio_manager.recording:
            self.audio_manager.stop_recording()
        
        # Clear text fields
        self.title_display.clear()
        self.raw_text.clear()
        self.formatted_text.clear()
        
        # Reset buttons and labels
        self.record_button.setText("Record")
        self.pause_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        self.recording_time_label.setText("00:00")
        self.recording_timer.stop()
        self.update_status("Reset complete", color=COLORS['secondary'])

    def update_recording_time(self):
        """Update the recording time display."""
        elapsed = int(time.time() - self.recording_start_time)
        minutes = elapsed // 60
        seconds = elapsed % 60
        self.recording_time_label.setText(f"{minutes:02d}:{seconds:02d}")

    def on_transcription_complete(self, text):
        self.raw_text.setText(text)
        self.update_status("Ready", COLORS['secondary'])

    def on_transcription_error(self, error):
        self.show_error("Transcription Error", str(error))
        self.update_status("Ready", COLORS['secondary'])

    def transcribe_audio(self):
        if not self.config.api_key:
            self.check_api_key()
            if not self.config.api_key:
                return

        audio_file = self.audio_manager.get_temp_file_path()
        if not audio_file:
            self.show_error("Error", "No audio recorded")
            self.update_status("Ready", COLORS['secondary'])
            return

        self.worker = TranscribeWorker(self.config.api_key, audio_file)
        self.worker.finished.connect(self.on_transcription_complete)
        self.worker.error.connect(self.on_transcription_error)
        self.worker.start()

    def format_text(self):
        """Format the transcribed text using GPT."""
        if not self.raw_text.toPlainText():
            self.show_error("Error", "No text to format")
            return
            
        self.update_status("Formatting text...", color=COLORS['accent'])
        self.format_button.setEnabled(False)
        
        self.format_worker = FormatWorker(
            self.config.api_key,
            self.raw_text.toPlainText(),
            self.config.get('gpt_temperature', 0.3)
        )
        self.format_worker.finished.connect(self._on_format_finished)
        self.format_worker.error.connect(self._on_format_error)
        self.format_worker.start()

    @pyqtSlot(str)
    def _on_format_finished(self, formatted_text):
        """Handle formatted text result."""
        try:
            # First try to find the title line
            lines = formatted_text.splitlines()
            title = ""
            content_start = 0
            
            # Find the title line and content start
            for i, line in enumerate(lines):
                if line.lower().startswith("title:"):
                    title = line.replace("Title:", "").replace("title:", "").strip()
                    content_start = i + 1
                    break
            
            # Skip any empty lines after title
            while content_start < len(lines) and not lines[content_start].strip():
                content_start += 1
                
            # Get the content
            content = "\n".join(lines[content_start:]).strip()
            
            if not title or not content:
                raise ValueError("Could not extract title and content from response")
            
            # Update the UI
            self.title_display.setText(title)
            self.formatted_text.setText(content)
            
            self.format_button.setEnabled(True)
            self.update_status("Text formatted successfully", color=COLORS['secondary'])
        except Exception as e:
            self._on_format_error(f"Error processing formatted text: {str(e)}")
            print("Debug - Full response:", formatted_text)  # For debugging

    @pyqtSlot(str)
    def _on_format_error(self, error):
        """Handle formatting error."""
        self.show_error("Text formatting failed", error)
        self.format_button.setEnabled(True)

    def download_text(self):
        """Download the formatted text using the title as filename"""
        if not self.formatted_text.toPlainText():
            self.show_error("Error", "No text to download")
            return

        title = self.title_display.text()
        if not title:
            self.show_error("Error", "No title generated")
            return

        # Clean the title for use as filename
        filename = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
        filename = filename.replace(' ', '_')
        
        # Save as markdown by default
        try:
            self.save_markdown(filename)
            self.update_status(f"Saved as {filename}.md", "green")
        except Exception as e:
            self.show_error("Save Error", str(e))

    def save_markdown(self, filename):
        content = f"# {self.title_display.text()}\n\n{self.formatted_text.toPlainText()}"
        download_path = Path(self.config.get("download_path", str(Path(os.path.expanduser("~/Desktop")))))
        path = download_path / f"{filename}.md"
        try:
            path.write_text(content)
            QMessageBox.information(self, "Success", f"File saved as {path}")
        except Exception as e:
            self.show_error("Error saving file", str(e))

    def clear_all(self):
        self.audio_manager.clear_recording()
        self.raw_text.clear()
        self.formatted_text.clear()
        self.title_display.clear()

    def setup_auto_save(self):
        self.auto_save_timer = QTimer()
        self.auto_save_timer.timeout.connect(self.auto_save)
        interval = self.config.get('auto_save_interval', 300) * 1000  # Convert to milliseconds
        self.auto_save_timer.start(interval)

    def auto_save(self):
        # TODO: Implement auto-save functionality
        pass

    def check_api_key(self):
        """Check if OpenAI API key is set and prompt user if not."""
        api_key = self.config.api_key
        if not api_key:
            self.show_settings()
            api_key = self.config.api_key
            if not api_key:
                self.show_error(
                    "API Key Required",
                    "Please set your OpenAI API key in the settings (Ctrl+,)"
                )
        return bool(api_key)

    def show_error(self, title, message):
        QMessageBox.critical(self, title, message)

    def update_word_count(self):
        text = self.raw_text.toPlainText()
        word_count = len(text.split()) if text else 0
        self.word_count_label.setText(f"Words: {word_count}")

    def update_status(self, message, color="black"):
        self.status_bar.showMessage(message)

    def apply_stylesheet(self):
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {COLORS['background']};
            }}
            QPushButton {{
                background-color: {COLORS['primary']};
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['secondary']};
            }}
            QPushButton:disabled {{
                background-color: {COLORS['disabled']};
            }}
            QLabel {{
                color: {COLORS['text']};
            }}
            QTextEdit {{
                border: 1px solid {COLORS['disabled']};
                border-radius: 4px;
                padding: 4px;
            }}
            QComboBox {{
                border: 1px solid {COLORS['disabled']};
                border-radius: 4px;
                padding: 4px;
            }}
        """)