# JARVIS NEO rich Dynamic Space upgrader
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
path = ROOT / "assistant.py"
text = path.read_text(encoding="utf-8")

start = text.find("class DynamicSpaceWidget(QFrame):")
if start < 0:
    raise SystemExit("DynamicSpaceWidget introuvable")
next_class = re.search(r"^class \w+\(", text[start + 1:], re.MULTILINE)
if not next_class:
    raise SystemExit("Classe suivante introuvable")
end = start + 1 + next_class.start()

new_class = r'''class DynamicSpaceWidget(QFrame):
    """Espace riche: texte, images, sites, vidéos et liens détectés automatiquement."""
    image_loaded = pyqtSignal(str, bytes)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("DynamicSpace")
        self.setMinimumHeight(190)
        self.setMaximumHeight(430)
        self.setStyleSheet("""
            QFrame#DynamicSpace { background: rgba(0, 243, 255, 0.045); border: 1px solid rgba(0,243,255,0.30); border-radius: 12px; }
            QLabel { background: transparent; border: none; }
            QScrollArea { background: transparent; border: none; }
            QTextEdit { background: rgba(2,8,22,0.70); color: #dffaff; border: 1px solid rgba(0,243,255,0.18); border-radius: 10px; padding: 8px; }
        """)
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 8, 10, 8)
        root.setSpacing(6)

        self.header = QLabel("◈ DYNAMIC SPACE  ·  CONTENU CONTEXTUEL")
        self.header.setStyleSheet("color:#00f3ff; font-weight:bold; letter-spacing:1px;")
        root.addWidget(self.header)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.body = QWidget()
        self.body_layout = QVBoxLayout(self.body)
        self.body_layout.setContentsMargins(2, 2, 2, 2)
        self.body_layout.setSpacing(8)
        self.body_layout.addStretch()
        self.scroll.setWidget(self.body)
        root.addWidget(self.scroll, 1)

        self.image_loaded.connect(self._apply_image)

    def _clear_body(self):
        while self.body_layout.count():
            item = self.body_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def _card(self, title, widget):
        frame = QFrame()
        frame.setStyleSheet("QFrame { background: rgba(5,16,38,0.88); border: 1px solid rgba(0,243,255,0.16); border-radius: 10px; }")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(10, 8, 10, 8)
        if title:
            label = QLabel(title)
            label.setStyleSheet("color:#00ffaa; font-weight:bold;")
            layout.addWidget(label)
        layout.addWidget(widget)
        self.body_layout.insertWidget(max(0, self.body_layout.count() - 1), frame)
        return frame

    @staticmethod
    def _urls(text):
        return list(dict.fromkeys(re.findall(r"https?://[^\s<>\]\)]+", text)))

    @staticmethod
    def _image_urls(text):
        return [u for u in DynamicSpaceWidget._urls(text) if re.search(r"\.(?:png|jpe?g|gif|webp|bmp)(?:\?.*)?$", u, re.I)]

    @staticmethod
    def _video_urls(text):
        urls = DynamicSpaceWidget._urls(text)
        out = []
        for u in urls:
            if re.search(r"\.(?:mp4|webm|mov|m3u8)(?:\?.*)?$", u, re.I) or any(host in u.lower() for host in ("youtube.com", "youtu.be", "vimeo.com", "dailymotion.com")):
                out.append(u)
        return out

    def _text_card(self, text):
        editor = QTextEdit()
        editor.setReadOnly(True)
        editor.setMinimumHeight(min(210, max(90, 34 + text.count("\n") * 18)))
        safe = html.escape(text)
        safe = re.sub(r"`([^`]+)`", r"<code>\1</code>", safe)
        safe = safe.replace("\n", "<br>")
        editor.setHtml(f"<div style='font-size:13px;line-height:1.45'>{safe}</div>")
        self._card("📝 TEXTE", editor)

    def _add_link_cards(self, urls, video_urls, image_urls):
        media = set(image_urls + video_urls)
        for url in urls:
            if url in media:
                continue
            if WEBENGINE_OK:
                view = QWebEngineView()
                view.setMinimumHeight(230)
                view.setMaximumHeight(300)
                view.setUrl(QUrl(url))
                self._card(f"🌐 SITE · {url}", view)
            else:
                label = QLabel(f"🌐 {url}")
                label.setWordWrap(True)
                label.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
                label.setOpenExternalLinks(True)
                self._card("🌐 SITE", label)

    def _add_videos(self, urls):
        for url in urls[:3]:
            if WEBENGINE_OK:
                view = QWebEngineView()
                view.setMinimumHeight(220)
                view.setMaximumHeight(300)
                view.setUrl(QUrl(url))
                self._card("▶ VIDÉO", view)
            else:
                label = QLabel(f"▶ {url}")
                label.setWordWrap(True)
                label.setOpenExternalLinks(True)
                self._card("▶ VIDÉO", label)

    def _add_images(self, urls):
        for url in urls[:6]:
            label = QLabel("⏳ Chargement de l'image…")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setMinimumHeight(100)
            label.setWordWrap(True)
            self._card("🖼 IMAGE", label)
            threading.Thread(target=self._download_image, args=(url,), daemon=True).start()

    def _download_image(self, url):
        try:
            response = requests.get(url, timeout=8, headers={"User-Agent": "JARVIS-NEO/3.6"})
            if response.ok and response.content:
                self.image_loaded.emit(url, response.content)
        except Exception as exc:
            logging.debug("Dynamic Space image load failed: %s", exc)

    def _apply_image(self, url, data):
        pixmap = QPixmap()
        if not pixmap.loadFromData(data):
            return
        for i in range(self.body_layout.count()):
            frame = self.body_layout.itemAt(i).widget()
            if not frame:
                continue
            for child in frame.findChildren(QLabel):
                if child.text().startswith("⏳ Chargement"):
                    child.setPixmap(pixmap.scaled(700, 260, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                    child.setText("")
                    return

    def update_from_response(self, message):
        text = str(message or "").strip()
        if not text:
            return
        self._clear_body()
        urls = self._urls(text)
        image_urls = self._image_urls(text)
        video_urls = self._video_urls(text)
        self.header.setText(f"◈ DYNAMIC SPACE  ·  {len(urls)} LIEN(S)  ·  {len(image_urls)} IMAGE(S)  ·  {len(video_urls)} VIDÉO(S)")
        self._text_card(text)
        self._add_images(image_urls)
        self._add_videos(video_urls)
        self._add_link_cards(urls, video_urls, image_urls)
        self.scroll.verticalScrollBar().setValue(self.scroll.verticalScrollBar().maximum())
'''

path.write_text(text[:start] + new_class + "\n\n" + text[end:], encoding="utf-8")
print("Dynamic Space rich renderer applied")
