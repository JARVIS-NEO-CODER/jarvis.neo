from pathlib import Path

path = Path("assistant.py")
text = path.read_text(encoding="utf-8")

# Safe HTML rendering for long model responses.
old_import = "import hashlib\nimport hmac\n"
new_import = "import hashlib\nimport hmac\nimport html\n"
if old_import not in text:
    raise SystemExit("import anchor not found")
text = text.replace(old_import, new_import, 1)

# Add a real Dynamic Space between the HUD toolbar and the chat.
anchor = "class JarvisWindow(QMainWindow):\n"
if anchor not in text:
    raise SystemExit("JarvisWindow anchor not found")

dynamic_class = '''class DynamicSpaceWidget(QFrame):\n    """Dynamic contextual panel driven automatically by JARVIS responses."""\n    def __init__(self, parent=None):\n        super().__init__(parent)\n        self.setObjectName("DynamicSpace")\n        self.setMaximumHeight(220)\n        self.setStyleSheet("""\n            QFrame#DynamicSpace {\n                background: rgba(0, 243, 255, 0.055);\n                border: 1px solid rgba(0, 243, 255, 0.35);\n                border-radius: 12px;\n            }\n            QLabel { background: transparent; border: none; }\n            QTextEdit {\n                background: transparent; border: none; color: #dff9ff;\n                font-family: 'Segoe UI', sans-serif; font-size: 12px;\n                padding: 4px 8px;\n            }\n        """)\n        layout = QVBoxLayout(self)\n        layout.setContentsMargins(12, 8, 12, 10)\n        layout.setSpacing(5)\n\n        header = QHBoxLayout()\n        title = QLabel("◈ DYNAMIC SPACE")\n        title.setStyleSheet("color:#00f3ff; font-size:10px; font-weight:bold; letter-spacing:1.5px;")\n        self.meta = QLabel("EN ATTENTE")\n        self.meta.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)\n        self.meta.setStyleSheet("color:#6f9baa; font-size:9px;")\n        header.addWidget(title)\n        header.addStretch()\n        header.addWidget(self.meta)\n        layout.addLayout(header)\n\n        self.content = QTextEdit()\n        self.content.setReadOnly(True)\n        self.content.setAcceptRichText(False)\n        self.content.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)\n        self.content.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)\n        self.content.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)\n        self.content.setPlaceholderText("JARVIS alimentera cet espace automatiquement.")\n        layout.addWidget(self.content)\n\n    def update_from_response(self, message):\n        text = str(message or "").strip()\n        if not text:\n            return\n        # Keep the Dynamic Space useful rather than duplicating the whole chat.\n        lines = [line.strip() for line in text.splitlines() if line.strip()]\n        bullets = [line for line in lines if line.startswith(("- ", "• ", "* ", "1. ", "2. ", "3. "))]\n        if bullets:\n            preview = "\\n".join(bullets[:8])\n        else:\n            preview = " ".join(lines)\n        if len(preview) > 900:\n            preview = preview[:897].rstrip() + "…"\n        self.content.setPlainText(preview)\n        self.meta.setText(f"{len(text):,} CARACTÈRES".replace(",", " "))\n        self.content.verticalScrollBar().setValue(self.content.verticalScrollBar().maximum())\n\n'''
text = text.replace(anchor, dynamic_class + anchor, 1)

# Instantiate the Dynamic Space directly in the right panel.
old_stack = '''        # NOTE : Ici nous créons un conteneur intelligent pour basculer facilement entre le Chat IA et le Navigateur Web Natif intégré\n        self.content_stack_layout = QVBoxLayout()\n        \n        # 1. Zone de Chat standard\n        self.chat_display = QTextEdit()\n        self.chat_display.setReadOnly(True)\n        self.content_stack_layout.addWidget(self.chat_display)\n'''
new_stack = '''        # Dynamic Space: alimenté automatiquement par les réponses de JARVIS.\n        self.dynamic_space = DynamicSpaceWidget()\n        self.right_panel.addWidget(self.dynamic_space)\n\n        # Conteneur intelligent pour basculer entre Chat IA et navigateur natif.\n        self.content_stack_layout = QVBoxLayout()\n        \n        # Zone de Chat robuste pour les réponses longues.\n        self.chat_display = QTextEdit()\n        self.chat_display.setReadOnly(True)\n        self.chat_display.setAcceptRichText(True)\n        self.chat_display.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)\n        self.chat_display.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)\n        self.chat_display.setUndoRedoEnabled(False)\n        self.content_stack_layout.addWidget(self.chat_display)\n'''
if old_stack not in text:
    raise SystemExit("chat stack anchor not found")
text = text.replace(old_stack, new_stack, 1)

# Escape model output before inserting it into HTML. Preserve line breaks explicitly.
old_append = '''        self.chat_display.append(bubble)\n        self.chat_display.verticalScrollBar().setValue(self.chat_display.verticalScrollBar().maximum())\n'''
new_append = '''        if sender in ("Jarvis", "J.A.R.V.I.S."):\n            self.dynamic_space.update_from_response(msg)\n\n        # Model output is untrusted text: escape it before placing it in the bubble HTML.\n        safe_msg = html.escape(str(msg)).replace("\\n", "<br>")\n        bubble = bubble.replace(str(msg), safe_msg)\n        self.chat_display.insertHtml(bubble)\n        self.chat_display.insertHtml("<div style='height:2px;'></div>")\n        self.chat_display.verticalScrollBar().setValue(self.chat_display.verticalScrollBar().maximum())\n'''
if old_append not in text:
    raise SystemExit("chat append anchor not found")
text = text.replace(old_append, new_append, 1)

path.write_text(text, encoding="utf-8")
print("UI patch applied")
