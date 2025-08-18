import sys
import json
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QTextEdit, QMenuBar, 
                            QFileDialog, QMessageBox, QToolBar, QStatusBar,
                            QVBoxLayout, QWidget, QTabWidget, QSplitter,
                            QDialog, QLabel, QLineEdit, QPushButton)
from PyQt6.QtGui import QIcon, QTextCursor, QSyntaxHighlighter, QTextCharFormat, QColor, QFont
from PyQt6.QtCore import Qt, QRegularExpression
import openai
import requests
from datetime import datetime

class CodeHighlighter(QSyntaxHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.highlighting_rules = []
        
        # Python syntax highlighting
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor(255, 100, 100))
        keyword_format.setFontWeight(QFont.Weight.Bold)
        keywords = [
            'and', 'as', 'assert', 'break', 'class', 'continue', 'def', 'del',
            'elif', 'else', 'except', 'False', 'finally', 'for', 'from', 'global',
            'if', 'import', 'in', 'is', 'lambda', 'None', 'nonlocal', 'not',
            'or', 'pass', 'raise', 'return', 'True', 'try', 'while', 'with', 'yield'
        ]
        for word in keywords:
            pattern = QRegularExpression(r'\b' + word + r'\b')
            self.highlighting_rules.append((pattern, keyword_format))
        
        # Strings
        string_format = QTextCharFormat()
        string_format.setForeground(QColor(100, 255, 100))
        self.highlighting_rules.append((QRegularExpression(r'\".*\"'), string_format))
        self.highlighting_rules.append((QRegularExpression(r'\'.*\''), string_format))
        
        # Comments
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor(150, 150, 150))
        self.highlighting_rules.append((QRegularExpression(r'#.*'), comment_format))

    def highlightBlock(self, text):
        for pattern, format in self.highlighting_rules:
            match_iterator = pattern.globalMatch(text)
            while match_iterator.hasNext():
                match = match_iterator.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), format)

class LLMIntegration:
    def __init__(self, api_key=None):
        self.api_key = api_key
        self.model = "gpt-4"
        
    def set_api_key(self, api_key):
        self.api_key = api_key
        
    def query(self, prompt, max_tokens=150):
        if not self.api_key:
            return "Error: No API key configured"
            
        try:
            openai.api_key = self.api_key
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error: {str(e)}"

class TelegramIntegration:
    def __init__(self, token=None, chat_id=None):
        self.token = token
        self.chat_id = chat_id
        
    def send_message(self, text):
        if not self.token or not self.chat_id:
            return False
            
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        params = {
            'chat_id': self.chat_id,
            'text': text
        }
        
        try:
            response = requests.post(url, params=params)
            return response.status_code == 200
        except Exception:
            return False

class InvoiceGenerator:
    def generate_invoice(self, client_name, items, total_amount):
        invoice = f"""
        INVOICE
        Date: {datetime.now().strftime('%Y-%m-%d')}
        Client: {client_name}
        
        ITEMS:
        """
        
        for item in items:
            invoice += f"{item['name']} - {item['quantity']} x ${item['price']:.2f} = ${item['quantity'] * item['price']:.2f}\n"
            
        invoice += f"\nTOTAL AMOUNT: ${total_amount:.2f}"
        return invoice

class AccurateNotepad(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Accurate Notepad")
        self.setGeometry(100, 100, 800, 600)
        
        # Red theme
        self.setStyleSheet("""
            QMainWindow {
                background-color: #330000;
            }
            QTextEdit {
                background-color: #1a0000;
                color: #ffffff;
                font-family: Consolas;
                font-size: 12pt;
            }
            QMenuBar {
                background-color: #660000;
                color: white;
            }
            QMenuBar::item:selected {
                background-color: #990000;
            }
            QMenu {
                background-color: #660000;
                color: white;
            }
            QMenu::item:selected {
                background-color: #990000;
            }
            QStatusBar {
                background-color: #660000;
                color: white;
            }
            QTabWidget::pane {
                border: 1px solid #990000;
                background: #330000;
            }
            QTabBar::tab {
                background: #660000;
                color: white;
                padding: 8px;
            }
            QTabBar::tab:selected {
                background: #990000;
            }
        """)
        
        # Core components
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.setCentralWidget(self.tabs)
        
        # Initialize modules
        self.llm = LLMIntegration()
        self.telegram = TelegramIntegration()
        self.invoice_generator = InvoiceGenerator()
        
        # File management
        self.current_files = {}  # tab index: filepath
        
        # Create menu bar
        self.create_menu_bar()
        
        # Create toolbar
        self.create_toolbar()
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Add first tab
        self.add_new_tab()
        
        # Settings
        self.settings = {
            'llm_api_key': None,
            'telegram_token': None,
            'telegram_chat_id': None,
            'theme': 'red',
            'font_size': 12
        }
        
        # Load settings if they exist
        self.load_settings()
    
    def create_menu_bar(self):
        menu_bar = QMenuBar()
        
        # File menu
        file_menu = menu_bar.addMenu("File")
        
        new_tab_action = file_menu.addAction("New Tab")
        new_tab_action.triggered.connect(self.add_new_tab)
        
        open_action = file_menu.addAction("Open")
        open_action.triggered.connect(self.open_file)
        
        save_action = file_menu.addAction("Save")
        save_action.triggered.connect(self.save_file)
        
        save_as_action = file_menu.addAction("Save As")
        save_as_action.triggered.connect(self.save_file_as)
        
        file_menu.addSeparator()
        
        exit_action = file_menu.addAction("Exit")
        exit_action.triggered.connect(self.close)
        
        # Edit menu
        edit_menu = menu_bar.addMenu("Edit")
        
        undo_action = edit_menu.addAction("Undo")
        undo_action.triggered.connect(self.undo)
        
        redo_action = edit_menu.addAction("Redo")
        redo_action.triggered.connect(self.redo)
        
        edit_menu.addSeparator()
        
        cut_action = edit_menu.addAction("Cut")
        cut_action.triggered.connect(self.cut)
        
        copy_action = edit_menu.addAction("Copy")
        copy_action.triggered.connect(self.copy)
        
        paste_action = edit_menu.addAction("Paste")
        paste_action.triggered.connect(self.paste)
        
        # View menu
        view_menu = menu_bar.addMenu("View")
        
        zoom_in_action = view_menu.addAction("Zoom In")
        zoom_in_action.triggered.connect(self.zoom_in)
        
        zoom_out_action = view_menu.addAction("Zoom Out")
        zoom_out_action.triggered.connect(self.zoom_out)
        
        # Tools menu
        tools_menu = menu_bar.addMenu("Tools")
        
        llm_query_action = tools_menu.addAction("LLM Query")
        llm_query_action.triggered.connect(self.llm_query)
        
        generate_invoice_action = tools_menu.addAction("Generate Invoice")
        generate_invoice_action.triggered.connect(self.generate_invoice_dialog)
        
        send_to_telegram_action = tools_menu.addAction("Send to Telegram")
        send_to_telegram_action.triggered.connect(self.send_to_telegram)
        
        # Settings menu
        settings_menu = menu_bar.addMenu("Settings")
        
        configure_llm_action = settings_menu.addAction("Configure LLM")
        configure_llm_action.triggered.connect(self.configure_llm)
        
        configure_telegram_action = settings_menu.addAction("Configure Telegram")
        configure_telegram_action.triggered.connect(self.configure_telegram)
        
        # Help menu
        help_menu = menu_bar.addMenu("Help")
        
        about_action = help_menu.addAction("About")
        about_action.triggered.connect(self.show_about)
        
        self.setMenuBar(menu_bar)
    
    def create_toolbar(self):
        toolbar = QToolBar("Main Toolbar")
        self.addToolBar(toolbar)
        
        # Add actions to toolbar
        new_tab_action = toolbar.addAction(QIcon.fromTheme("document-new"), "New Tab")
        new_tab_action.triggered.connect(self.add_new_tab)
        
        open_action = toolbar.addAction(QIcon.fromTheme("document-open"), "Open")
        open_action.triggered.connect(self.open_file)
        
        save_action = toolbar.addAction(QIcon.fromTheme("document-save"), "Save")
        save_action.triggered.connect(self.save_file)
        
        toolbar.addSeparator()
        
        cut_action = toolbar.addAction(QIcon.fromTheme("edit-cut"), "Cut")
        cut_action.triggered.connect(self.cut)
        
        copy_action = toolbar.addAction(QIcon.fromTheme("edit-copy"), "Copy")
        copy_action.triggered.connect(self.copy)
        
        paste_action = toolbar.addAction(QIcon.fromTheme("edit-paste"), "Paste")
        paste_action.triggered.connect(self.paste)
        
        toolbar.addSeparator()
        
        llm_action = toolbar.addAction(QIcon.fromTheme("system-run"), "LLM Query")
        llm_action.triggered.connect(self.llm_query)
    
    def add_new_tab(self, content="", title="Untitled"):
        text_edit = QTextEdit()
        text_edit.setAcceptRichText(False)
        
        # Set syntax highlighter
        highlighter = CodeHighlighter(text_edit.document())
        
        index = self.tabs.addTab(text_edit, title)
        self.tabs.setCurrentIndex(index)
        
        if content:
            text_edit.setPlainText(content)
        
        return index
    
    def close_tab(self, index):
        if self.tabs.count() == 1:
            self.add_new_tab()
        
        if index in self.current_files:
            del self.current_files[index]
        
        self.tabs.removeTab(index)
    
    def get_current_editor(self):
        return self.tabs.currentWidget()
    
    def open_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open File", "", 
                                                  "Text Files (*.txt);;Python Files (*.py);;All Files (*)")
        
        if file_path:
            try:
                with open(file_path, 'r') as file:
                    content = file.read()
                    
                    index = self.add_new_tab(content, os.path.basename(file_path))
                    self.current_files[index] = file_path
                    
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not open file: {str(e)}")
    
    def save_file(self):
        current_index = self.tabs.currentIndex()
        current_editor = self.get_current_editor()
        
        if not current_editor:
            return
            
        if current_index in self.current_files:
            file_path = self.current_files[current_index]
            try:
                with open(file_path, 'w') as file:
                    file.write(current_editor.toPlainText())
                    
                self.status_bar.showMessage(f"File saved: {file_path}", 3000)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not save file: {str(e)}")
        else:
            self.save_file_as()
    
    def save_file_as(self):
        current_editor = self.get_current_editor()
        if not current_editor:
            return
            
        file_path, _ = QFileDialog.getSaveFileName(self, "Save File", "", 
                                                  "Text Files (*.txt);;Python Files (*.py);;All Files (*)")
        
        if file_path:
            try:
                with open(file_path, 'w') as file:
                    file.write(current_editor.toPlainText())
                    
                current_index = self.tabs.currentIndex()
                self.current_files[current_index] = file_path
                self.tabs.setTabText(current_index, os.path.basename(file_path))
                
                self.status_bar.showMessage(f"File saved: {file_path}", 3000)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not save file: {str(e)}")
    
    def undo(self):
        current_editor = self.get_current_editor()
        if current_editor:
            current_editor.undo()
    
    def redo(self):
        current_editor = self.get_current_editor()
        if current_editor:
            current_editor.redo()
    
    def cut(self):
        current_editor = self.get_current_editor()
        if current_editor:
            current_editor.cut()
    
    def copy(self):
        current_editor = self.get_current_editor()
        if current_editor:
            current_editor.copy()
    
    def paste(self):
        current_editor = self.get_current_editor()
        if current_editor:
            current_editor.paste()
    
    def zoom_in(self):
        current_editor = self.get_current_editor()
        if current_editor:
            font = current_editor.font()
            font.setPointSize(font.pointSize() + 1)
            current_editor.setFont(font)
    
    def zoom_out(self):
        current_editor = self.get_current_editor()
        if current_editor:
            font = current_editor.font()
            font.setPointSize(max(8, font.pointSize() - 1))
            current_editor.setFont(font)
    
    def llm_query(self):
        current_editor = self.get_current_editor()
        if not current_editor:
            return
            
        selected_text = current_editor.textCursor().selectedText()
        if not selected_text:
            QMessageBox.information(self, "Info", "Please select some text to query the LLM")
            return
            
        if not self.settings['llm_api_key']:
            self.configure_llm()
            if not self.settings['llm_api_key']:
                return
                
        response = self.llm.query(selected_text)
        
        # Add response in a new tab
        self.add_new_tab(response, "LLM Response")
    
    def generate_invoice_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Generate Invoice")
        dialog.setModal(True)
        
        layout = QVBoxLayout()
        
        # Client name
        layout.addWidget(QLabel("Client Name:"))
        client_name_edit = QLineEdit()
        layout.addWidget(client_name_edit)
        
        # Items (simplified for this example)
        layout.addWidget(QLabel("Items (format: name,quantity,price per item)"))
        items_edit = QTextEdit()
        items_edit.setPlainText("Item 1,2,10.50\nItem 2,1,25.00")
        layout.addWidget(items_edit)
        
        # Generate button
        generate_btn = QPushButton("Generate Invoice")
        generate_btn.clicked.connect(lambda: self.generate_invoice(
            client_name_edit.text(),
            items_edit.toPlainText(),
            dialog
        ))
        layout.addWidget(generate_btn)
        
        dialog.setLayout(layout)
        dialog.exec()
    
    def generate_invoice(self, client_name, items_text, dialog):
        try:
            items = []
            for line in items_text.split('\n'):
                if line.strip():
                    name, quantity, price = line.split(',')
                    items.append({
                        'name': name.strip(),
                        'quantity': int(quantity.strip()),
                        'price': float(price.strip())
                    })
            
            total = sum(item['quantity'] * item['price'] for item in items)
            invoice = self.invoice_generator.generate_invoice(client_name, items, total)
            
            self.add_new_tab(invoice, f"Invoice_{client_name}")
            dialog.close()
        except Exception as e:
            QMessageBox.critical(dialog, "Error", f"Invalid input format: {str(e)}")
    
    def send_to_telegram(self):
        current_editor = self.get_current_editor()
        if not current_editor:
            return
            
        selected_text = current_editor.textCursor().selectedText()
        if not selected_text:
            selected_text = current_editor.toPlainText()
            
        if not selected_text:
            QMessageBox.information(self, "Info", "No text to send")
            return
            
        if not self.settings['telegram_token'] or not self.settings['telegram_chat_id']:
            self.configure_telegram()
            if not self.settings['telegram_token'] or not self.settings['telegram_chat_id']:
                return
                
        self.telegram.token = self.settings['telegram_token']
        self.telegram.chat_id = self.settings['telegram_chat_id']
        
        success = self.telegram.send_message(selected_text)
        if success:
            QMessageBox.information(self, "Success", "Message sent to Telegram")
        else:
            QMessageBox.critical(self, "Error", "Failed to send message to Telegram")
    
    def configure_llm(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Configure LLM")
        dialog.setModal(True)
        
        layout = QVBoxLayout()
        
        layout.addWidget(QLabel("LLM API Key:"))
        api_key_edit = QLineEdit()
        api_key_edit.setPlaceholderText("Enter your LLM API key")
        if self.settings['llm_api_key']:
            api_key_edit.setText(self.settings['llm_api_key'])
        layout.addWidget(api_key_edit)
        
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(lambda: self.save_llm_config(
            api_key_edit.text(),
            dialog
        ))
        layout.addWidget(save_btn)
        
        dialog.setLayout(layout)
        dialog.exec()
    
    def save_llm_config(self, api_key, dialog):
        self.settings['llm_api_key'] = api_key.strip()
        self.llm.set_api_key(api_key.strip())
        self.save_settings()
        dialog.close()
        QMessageBox.information(self, "Success", "LLM configuration saved")
    
    def configure_telegram(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Configure Telegram")
        dialog.setModal(True)
        
        layout = QVBoxLayout()
        
        layout.addWidget(QLabel("Telegram Bot Token:"))
        token_edit = QLineEdit()
        token_edit.setPlaceholderText("Enter your Telegram bot token")
        if self.settings['telegram_token']:
            token_edit.setText(self.settings['telegram_token'])
        layout.addWidget(token_edit)
        
        layout.addWidget(QLabel("Chat ID:"))
        chat_id_edit = QLineEdit()
        chat_id_edit.setPlaceholderText("Enter your Telegram chat ID")
        if self.settings['telegram_chat_id']:
            chat_id_edit.setText(self.settings['telegram_chat_id'])
        layout.addWidget(chat_id_edit)
        
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(lambda: self.save_telegram_config(
            token_edit.text(),
            chat_id_edit.text(),
            dialog
        ))
        layout.addWidget(save_btn)
        
        dialog.setLayout(layout)
        dialog.exec()
    
    def save_telegram_config(self, token, chat_id, dialog):
        self.settings['telegram_token'] = token.strip()
        self.settings['telegram_chat_id'] = chat_id.strip()
        self.save_settings()
        dialog.close()
        QMessageBox.information(self, "Success", "Telegram configuration saved")
    
    def load_settings(self):
        try:
            if os.path.exists('notepad_settings.json'):
                with open('notepad_settings.json', 'r') as f:
                    self.settings = json.load(f)
                    
                # Update modules with loaded settings
                self.llm.set_api_key(self.settings.get('llm_api_key', ''))
                self.telegram.token = self.settings.get('telegram_token', '')
                self.telegram.chat_id = self.settings.get('telegram_chat_id', '')
        except Exception:
            pass  # Use default settings if loading fails
    
    def save_settings(self):
        try:
            with open('notepad_settings.json', 'w') as f:
                json.dump(self.settings, f)
        except Exception as e:
            print(f"Error saving settings: {str(e)}")
    
    def show_about(self):
        QMessageBox.about(self, "About Accurate Notepad",
                         "Accurate Notepad\n\n"
                         "A feature-rich text editor with:\n"
                         "- Code editing with syntax highlighting\n"
                         "- LLM integration\n"
                         "- Telegram integration\n"
                         "- Invoice generation\n"
                         "- Customizable interface")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    notepad = AccurateNotepad()
    notepad.show()
    sys.exit(app.exec())