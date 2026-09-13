from pathlib import Path
p=Path('assistant.py')
s=p.read_text(encoding='utf-8')
needle='        self.left_panel.addStretch()\n        \n        btn_exit = GlowButton("DÉCONNECTER LE SYSTÈME", QColor(255, 50, 50))'
if needle not in s: raise SystemExit('HUD insertion point not found')
block='''        self.left_panel.addSpacing(8)\n        hud_label = QLabel("CENTRE DE COMMANDE")\n        hud_label.setStyleSheet("font-size: 10px; color: #00f3ff; font-weight: bold; letter-spacing: 1.5px;")\n        self.left_panel.addWidget(hud_label)\n        hud_grid = QGridLayout()\n        hud_grid.setSpacing(5)\n        hud_actions = [\n            ("🌤 MÉTÉO", "météo"), ("🕒 HEURE", "quelle heure est-il"),\n            ("📅 DATE", "quelle est la date"), ("🔋 BATTERIE", "batterie"),\n            ("🖥 SYSTÈME", "système"), ("📊 PROCESSUS", "processus"),\n            ("📝 TÂCHES", "tâches"), ("🧠 MÉMOIRE", "mémos"),\n            ("📆 AGENDA", "agenda"), ("🔎 WEB", "recherche web"),\n            ("👁 ÉCRAN", "analyse l'écran"), ("🔌 PLUGINS", "liste les plugins"),\n            ("🛡 SÉCURITÉ", "sécurité on"), ("👂 ÉCOUTE", "écoute passive on"),\n            ("🧹 CHAT", "vider le chat"), ("❓ AIDE", "aide"),\n        ]\n        for i, (label, command) in enumerate(hud_actions):\n            b=GlowButton(label)\n            b.setFixedHeight(31)\n            b.setToolTip(f"Commande J.A.R.V.I.S. : {command}")\n            b.clicked.connect(lambda _, c=command: command_queue.put(c))\n            hud_grid.addWidget(b, i//2, i%2)\n        self.left_panel.addLayout(hud_grid)\n        \n        self.left_panel.addStretch()\n        \n        btn_exit = GlowButton("DÉCONNECTER LE SYSTÈME", QColor(255, 50, 50))'''
s=s.replace(needle,block,1)
p.write_text(s,encoding='utf-8')
compile(s,'assistant.py','exec')
