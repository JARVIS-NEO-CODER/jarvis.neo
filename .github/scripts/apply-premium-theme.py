from pathlib import Path


def replace_once(text, old, new, label):
    if old not in text:
        raise SystemExit(f'{label}: anchor not found')
    return text.replace(old, new, 1)

# --- assistant.py: premium theme + immediate voice handoff ---
p = Path('assistant.py')
s = p.read_text(encoding='utf-8')

import_line = 'from core.neo_theme import apply_theme'
if import_line not in s:
    anchor = 'from core.web_media import WebMediaProvider\n'
    s = replace_once(s, anchor, anchor + import_line + '\n', 'theme import')

hook = '    apply_theme(QApplication.instance(), window)\n'
s = s.replace('    apply_theme(QApplication.instance())\n', '')
s = s.replace('    apply_theme(app if \'app\' in globals() else application)\n', '')
s = s.replace(hook, '')
s = replace_once(s, '    window = JarvisWindow()\n', '    window = JarvisWindow()\n' + hook, 'theme hook')

# A command response is urgent: don't let a startup/reminder TTS item sit in front of it.
s = replace_once(s, '                speech.say(response)\n', '                speech.say(response, priority=True)\n', 'command TTS priority')

# Keep recognition responsive without recalibrating the microphone on every loop.
old_voice = '''    recognizer.phrase_threshold = 0.3\n\n    while True:\n'''
new_voice = '''    recognizer.phrase_threshold = 0.3\n    calibrated = False\n\n    while True:\n'''
s = replace_once(s, old_voice, new_voice, 'voice calibration state')
old_calibration = '                recognizer.adjust_for_ambient_noise(source, duration=0.4)\n'
new_calibration = '''                if not calibrated:\n                    recognizer.adjust_for_ambient_noise(source, duration=0.25)\n                    calibrated = True\n'''
s = replace_once(s, old_calibration, new_calibration, 'voice calibration')

p.write_text(s, encoding='utf-8')
compile(s, 'assistant.py', 'exec')

# --- core/assistant_components.py: make TTS startup cheap and queue urgent speech first ---
p = Path('core/assistant_components.py')
s = p.read_text(encoding='utf-8')
old_init = '''    def __init__(self):\n        self._lock = threading.Lock()\n        self.thread = threading.Thread(target=self._worker, daemon=True)\n        self.thread.start()\n'''
new_init = '''    def __init__(self):\n        self._lock = threading.Lock()\n        # Initialize the mixer once at startup instead of on the first answer.\n        # This removes a noticeable first-response audio delay.\n        if pygame:\n            try:\n                if not pygame.mixer.get_init():\n                    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)\n            except Exception:\n                pass\n        self.thread = threading.Thread(target=self._worker, daemon=True)\n        self.thread.start()\n'''
s = replace_once(s, old_init, new_init, 'SpeechEngine init')
old_say = '''    def say(self, text):\n        clean = re.sub(r"\\s+", " ", re.sub(r"https?://\\S+", "", str(text))).strip()\n        if clean: tts_queue.put(clean)\n'''
new_say = '''    def say(self, text, priority=False):\n        clean = re.sub(r"\\s+", " ", re.sub(r"https?://\\S+", "", str(text))).strip()\n        if not clean:\n            return\n        if priority:\n            # Never make a fresh command wait behind queued startup/reminder audio.\n            while True:\n                try:\n                    tts_queue.get_nowait()\n                    tts_queue.task_done()\n                except queue.Empty:\n                    break\n        tts_queue.put(clean)\n'''
s = replace_once(s, old_say, new_say, 'SpeechEngine.say')
# Mixer is already warm, so don't pay initialization cost in every _say call.
old_mixer = '                    if not pygame.mixer.get_init(): pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=1024)\n'
s = s.replace(old_mixer, '                    if not pygame.mixer.get_init(): pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)\n', 1)
p.write_text(s, encoding='utf-8')

compile(Path('core/assistant_components.py').read_text(encoding='utf-8'), 'core/assistant_components.py', 'exec')
print('Voice latency optimizations and premium theme hook installed.')
