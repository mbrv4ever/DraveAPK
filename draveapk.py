#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DraveAPK - bouw je Python/Kivy-app naar een Android-APK, met knoppen.

Onder water gebruikt DraveAPK het bestaande WSL2 + Buildozer dat je hebt opgezet;
jij ziet alleen knoppen en een voortgangslog - geen zwart CMD-venster.

Werkwijze: kies een projectmap (met main.py), vul naam/pakketnaam in, klik
"Bouw APK". DraveAPK kopieert het project naar de Linux-kant, draait Buildozer en
legt de klare .apk in een 'bin'-map in je project.

Vereist: Windows met WSL2 + Ubuntu waarin Buildozer is geinstalleerd
(zie AndroidTest/SETUP-Android.md). DraveAPK controleert dat met "Controleer omgeving".
"""
import os
import re
import sys
import json
import shutil

from PyQt6.QtCore import Qt, QLocale, QUrl, QProcess
from PyQt6.QtGui import QPixmap, QIcon, QDesktopServices, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton, QVBoxLayout,
    QHBoxLayout, QLineEdit, QPlainTextEdit, QFileDialog, QMessageBox, QDialog,
    QStatusBar, QToolButton, QTextBrowser)

APP_NAME = "DraveAPK"
APP_VERSION = "0.1"
DONATE_URL = "https://paypal.me/roger076"
SUPPORT_MAIL = "service@dravenlock.nl"
DEFAULT_DISTRO = "Ubuntu-22.04"

# ---- Dravenlock-huisstijl ----
BG = "#0e0e11"
PANEL = "#16161b"
SILVER = "#d4d4d4"
MUTE = "#8a8a94"
ACCENT = "#6fa3d6"
WARN = "#e0a23a"
OKGREEN = "#5fb87a"
REDC = "#d6705f"


def _app_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def _config_path():
    return os.path.join(_app_dir(), "draveapk_config.json")


DEFAULT_CONFIG = {"project": "", "distro": DEFAULT_DISTRO,
                  "domain": "nl.dravenlock", "requirements": "python3,kivy"}


def load_config():
    cfg = dict(DEFAULT_CONFIG)
    try:
        with open(_config_path(), "r", encoding="utf-8") as f:
            cfg.update(json.load(f))
    except Exception:
        pass
    return cfg


def save_config(cfg):
    try:
        with open(_config_path(), "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Hulpfuncties
# ---------------------------------------------------------------------------
def win_to_wsl(path):
    """C:\\Users\\x -> /mnt/c/Users/x ; D:\\a\\b -> /mnt/d/a/b"""
    p = path.replace("\\", "/")
    m = re.match(r"^([A-Za-z]):/(.*)$", p)
    if m:
        return "/mnt/" + m.group(1).lower() + "/" + m.group(2)
    return p


def safe_pkgname(name):
    s = re.sub(r"[^a-z0-9]", "", (name or "").lower())
    return s or "draveapp"


def _logo_path(name):
    for base in (_app_dir(), os.path.join(_app_dir(), "assets"),
                 os.path.join(_app_dir(), "..", "assets")):
        p = os.path.join(base, name)
        if os.path.exists(p):
            return p
    return None


def logo_pixmap(size=34):
    for n in ("logo_t.png", "logo.png"):
        p = _logo_path(n)
        if p:
            pm = QPixmap(p)
            if not pm.isNull():
                return pm.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio,
                                 Qt.TransformationMode.SmoothTransformation)
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    return pm


def app_icon():
    for n in ("app.ico", "logo.ico", "logo.png"):
        p = _logo_path(n)
        if p:
            ic = QIcon(p)
            if not ic.isNull():
                return ic
    return QIcon()


SPEC_TEMPLATE = """[app]
title = %(title)s
package.name = %(pkg)s
package.domain = %(domain)s
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ttf
version = 0.1
requirements = %(req)s
icon.filename = %%(source.dir)s/logo.png
orientation = portrait
fullscreen = 0

[android]
android.archs = arm64-v8a
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
"""


GUIDE_NL = """DraveAPK - Snelgids

DraveAPK maakt van je Python/Kivy-app een Android-bestand (.apk), met knoppen.
Het zware werk gebeurt in WSL2 + Buildozer (eenmalig opgezet); jij ziet alleen
de voortgang.

Voor je begint (eenmalig)
- Windows met WSL2 + Ubuntu, en daarin Buildozer geinstalleerd.
- Zie AndroidTest\\SETUP-Android.md als je dat nog niet hebt gedaan.
- Klik op 'Controleer omgeving' - groen betekent klaar.

Een APK bouwen
1. Kies je projectmap (de map met main.py van je app).
2. Vul een App-naam in. De pakketnaam wordt automatisch voorgesteld.
3. 'Vereisten' is wat je app nodig heeft (standaard: python3,kivy).
4. Klik 'Bouw APK'. De eerste keer duurt lang (Buildozer haalt de Android-
   gereedschappen op); daarna sneller. Volg de voortgang in het venster.
5. Klaar? De .apk staat in een 'bin'-map in je project. Zet die op je telefoon,
   sta 'installeren van onbekende bronnen' toe, en open de app.

Tips
- Heeft je project al een buildozer.spec, dan gebruikt DraveAPK die. Anders maakt
  hij er zelf een met de naam/pakketnaam/vereisten die je invult.
- Android-apps maak je het best in Kivy (touch). Je gewone PyQt-apps gaan niet
  zomaar mee.

Vragen of een tip? service@dravenlock.nl
"""


class GuideDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Snelgids")
        self.resize(640, 560)
        lay = QVBoxLayout(self)
        tb = QTextBrowser()
        tb.setObjectName("guide")
        tb.setPlainText(GUIDE_NL)
        lay.addWidget(tb)
        b = QPushButton("Sluiten")
        b.clicked.connect(self.accept)
        lay.addWidget(b, alignment=Qt.AlignmentFlag.AlignRight)


class DraveAPK(QMainWindow):
    def __init__(self, cfg):
        super().__init__()
        self.cfg = cfg
        self.proc = None
        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(app_icon())
        self.resize(960, 700)

        root = QWidget()
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(self._build_header())

        body = QWidget()
        bl = QVBoxLayout(body)
        bl.setContentsMargins(16, 12, 16, 8)
        bl.setSpacing(10)

        # projectmap
        r1 = QHBoxLayout()
        r1.addWidget(QLabel("Projectmap (met main.py):"))
        self.ed_project = QLineEdit(cfg.get("project", ""))
        r1.addWidget(self.ed_project, 1)
        b1 = QPushButton("Bladeren…")
        b1.clicked.connect(self._browse)
        r1.addWidget(b1)
        bl.addLayout(r1)

        # naam + pakket
        r2 = QHBoxLayout()
        r2.addWidget(QLabel("App-naam:"))
        self.ed_name = QLineEdit()
        self.ed_name.textChanged.connect(self._suggest_pkg)
        r2.addWidget(self.ed_name, 1)
        r2.addWidget(QLabel("Pakketnaam:"))
        self.ed_pkg = QLineEdit()
        r2.addWidget(self.ed_pkg, 1)
        bl.addLayout(r2)

        # app-icoon
        ri = QHBoxLayout()
        ri.addWidget(QLabel("App-icoon (.png):"))
        self.ed_icon = QLineEdit()
        self.ed_icon.setPlaceholderText("leeg = logo uit de projectmap, anders het Dravenlock-logo")
        ri.addWidget(self.ed_icon, 1)
        bi = QPushButton("Bladeren…")
        bi.clicked.connect(self._browse_icon)
        ri.addWidget(bi)
        bl.addLayout(ri)

        # vereisten
        r3 = QHBoxLayout()
        r3.addWidget(QLabel("Vereisten:"))
        self.ed_req = QLineEdit(cfg.get("requirements", "python3,kivy"))
        r3.addWidget(self.ed_req, 1)
        bl.addLayout(r3)

        # knoppen
        r4 = QHBoxLayout()
        self.btn_check = QPushButton("Controleer omgeving")
        self.btn_check.clicked.connect(self._check_env)
        r4.addWidget(self.btn_check)
        self.btn_build = QPushButton("Bouw APK")
        self.btn_build.setObjectName("primary")
        self.btn_build.clicked.connect(self._build)
        r4.addWidget(self.btn_build)
        self.btn_stop = QPushButton("Stop")
        self.btn_stop.clicked.connect(self._stop)
        self.btn_stop.setEnabled(False)
        r4.addWidget(self.btn_stop)
        r4.addStretch(1)
        bl.addLayout(r4)

        # log
        self.log = QPlainTextEdit()
        self.log.setObjectName("log")
        self.log.setReadOnly(True)
        bl.addWidget(self.log, 1)

        outer.addWidget(body, 1)
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("Klaar. Tip: klik eerst 'Controleer omgeving'.")

        QShortcut(QKeySequence("F1"), self).activated.connect(
            lambda: GuideDialog(self).exec())

    # ---- opbouw ----
    def _build_header(self):
        h = QWidget()
        h.setObjectName("header")
        lay = QHBoxLayout(h)
        lay.setContentsMargins(14, 8, 14, 8)
        logo = QLabel()
        logo.setPixmap(logo_pixmap(34))
        lay.addWidget(logo)
        title = QLabel(APP_NAME)
        title.setObjectName("title")
        lay.addWidget(title)
        ver = QLabel("v" + APP_VERSION)
        ver.setObjectName("ver")
        lay.addWidget(ver)
        lay.addStretch(1)
        for label, cb in (("Snelgids", lambda: GuideDialog(self).exec()),
                          ("Over", self._about)):
            b = QPushButton(label)
            b.setObjectName("headerbtn")
            b.clicked.connect(cb)
            lay.addWidget(b)
        dn = QToolButton()
        dn.setObjectName("donate")
        dn.setText("♥ Donatie")
        dn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(DONATE_URL)))
        lay.addWidget(dn)
        return h

    # ---- helpers ----
    def _log(self, text, color=None):
        if color:
            self.log.appendHtml('<span style="color:%s">%s</span>'
                                % (color, text.replace("<", "&lt;")))
        else:
            self.log.appendPlainText(text)
        self.log.verticalScrollBar().setValue(
            self.log.verticalScrollBar().maximum())

    def _browse(self):
        d = QFileDialog.getExistingDirectory(self, "Kies projectmap",
                                             self.ed_project.text() or "")
        if d:
            self.ed_project.setText(d)
            if not self.ed_name.text():
                self.ed_name.setText(os.path.basename(d))
            # icoon voorvullen met een logo dat al in de map staat
            if not self.ed_icon.text():
                for n in ("logo.png", "icon.png", "logo_t.png"):
                    p = os.path.join(d, n)
                    if os.path.isfile(p):
                        self.ed_icon.setText(p)
                        break

    def _browse_icon(self):
        start = self.ed_project.text() or ""
        p, _ = QFileDialog.getOpenFileName(self, "Kies een icoon (PNG)", start,
                                           "Afbeeldingen (*.png)")
        if p:
            self.ed_icon.setText(p)

    def _suggest_pkg(self, text):
        # alleen voorstellen als de gebruiker het pakketveld nog niet zelf vulde
        if not self.ed_pkg.text() or self.ed_pkg.property("auto"):
            self.ed_pkg.setText(safe_pkgname(text))
            self.ed_pkg.setProperty("auto", True)

    def _busy(self, on):
        self.btn_build.setEnabled(not on)
        self.btn_check.setEnabled(not on)
        self.btn_stop.setEnabled(on)

    # ---- WSL-proces ----
    def _run(self, script, on_done=None, label="Bezig…"):
        if self.proc is not None:
            QMessageBox.information(self, APP_NAME, "Er loopt al iets. Even wachten.")
            return
        self._busy(True)
        self.status.showMessage(label)
        self.proc = QProcess(self)
        self.proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self._done_cb = on_done

        def on_out():
            data = bytes(self.proc.readAll()).decode("utf-8", "replace")
            for line in data.splitlines():
                self._log(line)

        def on_fin(code, _status):
            self._log("")
            ok = (code == 0)
            self._log("[klaar, code %d]" % code, OKGREEN if ok else REDC)
            self.proc = None
            self._busy(False)
            if self._done_cb:
                self._done_cb(ok)

        def on_err(_e):
            self._log("Kon WSL niet starten. Is WSL2 + Ubuntu geinstalleerd?", REDC)
            self.proc = None
            self._busy(False)

        self.proc.readyRead.connect(on_out)
        self.proc.finished.connect(on_fin)
        self.proc.errorOccurred.connect(on_err)
        distro = self.cfg.get("distro", DEFAULT_DISTRO)
        self.proc.start("wsl.exe", ["-d", distro, "--", "bash", "-lc", script])

    def _stop(self):
        if self.proc is not None:
            self._log("Gestopt door gebruiker.", WARN)
            try:
                self.proc.kill()
            except Exception:
                pass

    # ---- acties ----
    def _check_env(self):
        self.log.clear()
        self._log("Omgeving controleren...")
        self._run("echo Ubuntu: $(lsb_release -ds 2>/dev/null); "
                  "echo -n 'Buildozer: '; buildozer --version 2>/dev/null "
                  "|| echo 'NIET GEVONDEN'",
                  on_done=self._after_check, label="Controleren…")

    def _after_check(self, ok):
        txt = self.log.toPlainText()
        if "NIET GEVONDEN" in txt or not ok:
            self._log("Buildozer is nog niet klaar in WSL. Volg eerst "
                      "AndroidTest\\SETUP-Android.md (stap 1-2).", WARN)
            self.status.showMessage("Omgeving nog niet compleet.")
        else:
            self._log("Omgeving ziet er goed uit. Je kunt bouwen.", OKGREEN)
            self.status.showMessage("Omgeving OK.")

    def _build(self):
        project = self.ed_project.text().strip()
        name = self.ed_name.text().strip() or os.path.basename(project)
        pkg = safe_pkgname(self.ed_pkg.text().strip() or name)
        req = self.ed_req.text().strip() or "python3,kivy"
        domain = self.cfg.get("domain", "nl.dravenlock")
        if not project or not os.path.isdir(project):
            QMessageBox.warning(self, APP_NAME, "Kies eerst een geldige projectmap.")
            return
        if not os.path.isfile(os.path.join(project, "main.py")):
            QMessageBox.warning(self, APP_NAME,
                                "In die map staat geen main.py. Een Kivy-app heeft "
                                "een main.py als startpunt.")
            return
        # buildozer.spec maken als die nog niet bestaat
        spec = os.path.join(project, "buildozer.spec")
        if not os.path.isfile(spec):
            # icoon regelen: gekozen icoon -> anders logo uit de map -> anders
            # het Dravenlock-logo. Het komt als logo.png in de projectmap, want
            # de spec verwijst naar logo.png.
            proj_logo = os.path.join(project, "logo.png")
            icon = self.ed_icon.text().strip()
            if not icon:
                icon = proj_logo if os.path.isfile(proj_logo) else (_logo_path("logo.png") or "")
            try:
                if icon and os.path.isfile(icon) and \
                        os.path.abspath(icon) != os.path.abspath(proj_logo):
                    shutil.copyfile(icon, proj_logo)
                if os.path.isfile(proj_logo):
                    self._log("App-icoon: %s" % os.path.basename(icon or proj_logo), MUTE)
                else:
                    self._log("Geen icoon gevonden - de app krijgt het standaard "
                              "Kivy-icoon.", WARN)
            except Exception as e:
                self._log("Kon icoon niet instellen: %s" % e, WARN)
            try:
                with open(spec, "w", encoding="utf-8") as f:
                    f.write(SPEC_TEMPLATE % {"title": name, "pkg": pkg,
                                             "domain": domain, "req": req})
                self._log("buildozer.spec aangemaakt.", MUTE)
            except Exception as e:
                QMessageBox.warning(self, APP_NAME, "Kon buildozer.spec niet maken:\n%s" % e)
                return
        else:
            self._log("Bestaande buildozer.spec gevonden - die wordt gebruikt "
                      "(inclusief het icoon dat daarin staat).", MUTE)
        # opslaan
        self.cfg["project"] = project
        self.cfg["requirements"] = req
        save_config(self.cfg)

        src = win_to_wsl(project)
        bdir = "DraveAPK-builds/" + safe_pkgname(name)
        self.log.clear()
        self._log("APK bouwen voor '%s'. De eerste keer kan dit lang duren..." % name)
        self._log("(Project: %s)" % project, MUTE)
        # script: kopieer naar Linux-thuismap, bouw, kopieer .apk terug naar project\bin
        script = (
            'set -e; '
            'mkdir -p ~/%(b)s; rm -rf ~/%(b)s; mkdir -p ~/%(b)s; '
            'cp -r "%(src)s"/. ~/%(b)s/; '
            'cd ~/%(b)s; '
            'buildozer -v android debug; '
            'mkdir -p "%(src)s/bin"; '
            'cp ~/%(b)s/bin/*.apk "%(src)s/bin/"; '
            'echo APK_GEKOPIEERD'
        ) % {"b": bdir, "src": src}
        self._run(script, on_done=self._after_build, label="APK bouwen…")

    def _after_build(self, ok):
        if ok and "APK_GEKOPIEERD" in self.log.toPlainText():
            binmap = os.path.join(self.ed_project.text().strip(), "bin")
            self._log("Gelukt! De .apk staat in: %s" % binmap, OKGREEN)
            self.status.showMessage("Klaar - APK staat in de 'bin'-map van je project.")
            QMessageBox.information(
                self, APP_NAME,
                "Klaar! De APK staat in:\n%s\n\nZet 'm op je telefoon, sta "
                "'installeren van onbekende bronnen' toe, en open de app." % binmap)
        else:
            self._log("Bouwen mislukt. Lees de laatste rode/Engelse regels hierboven; "
                      "stuur ze gerust door, dan kijk ik mee.", REDC)
            self.status.showMessage("Bouwen mislukt - zie de log.")

    def _about(self):
        QMessageBox.information(
            self, "Over",
            "%s v%s\n\nBouw je Python/Kivy-app naar Android (APK) via WSL+Buildozer.\n"
            "Dravenlock\n%s\n%s" % (APP_NAME, APP_VERSION, SUPPORT_MAIL, DONATE_URL))


QSS = """
* { font-family: 'Segoe UI', sans-serif; font-size: 15px; color: %(silver)s; }
QMainWindow, QWidget { background: %(bg)s; }
#header { background: %(panel)s; border-bottom: 1px solid #23232b; }
#title { font-size: 20px; font-weight: 700; }
#ver { color: %(mute)s; font-size: 12px; }
QPushButton { background: %(panel)s; border: 1px solid #2c2c36; border-radius: 8px;
              padding: 9px 15px; color: %(silver)s; }
QPushButton:hover { border-color: %(accent)s; }
QPushButton:disabled { color: #5a5a63; border-color: #23232b; }
QPushButton#primary { background: %(accent)s; color: #08131f; font-weight: 700;
                      border: none; padding: 10px 20px; font-size: 16px; }
QPushButton#primary:hover { background: #87b6e3; }
QPushButton#headerbtn { padding: 6px 11px; }
QToolButton#donate { border: none; background: transparent; color: %(accent)s; }
QLineEdit { background: #1a1a20; border: 1px solid #2c2c36; border-radius: 8px;
    padding: 8px; color: %(silver)s; selection-background-color: %(accent)s;
    selection-color: #08131f; }
QLineEdit:focus { border-color: %(accent)s; }
QPlainTextEdit#log, QTextBrowser#guide { background: #121217; border: 1px solid #2c2c36;
    border-radius: 8px; padding: 8px; color: #cfd2d6;
    font-family: 'Consolas','Courier New',monospace; font-size: 13px; }
QStatusBar { background: %(panel)s; color: %(mute)s; }
QDialog { background: %(bg)s; }
""" % {"bg": BG, "panel": PANEL, "silver": SILVER, "mute": MUTE,
       "accent": ACCENT, "warn": WARN}


def _install_excepthook():
    import traceback

    def hook(exctype, value, tb):
        msg = "".join(traceback.format_exception(exctype, value, tb))
        try:
            with open(os.path.join(_app_dir(), "draveapk-fout.txt"),
                      "w", encoding="utf-8") as f:
                f.write(msg)
        except Exception:
            pass
        try:
            if QApplication.instance():
                QMessageBox.critical(None, APP_NAME + " - fout",
                                     "Er ging iets mis:\n\n" + msg[-1500:])
        except Exception:
            pass
        sys.__excepthook__(exctype, value, tb)

    sys.excepthook = hook


def main():
    _install_excepthook()
    if os.name == "nt":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                "Dravenlock.DraveAPK")
        except Exception:
            pass
    app = QApplication(sys.argv)
    try:
        cfg = load_config()
        app.setStyleSheet(QSS)
        app.setWindowIcon(app_icon())
        win = DraveAPK(cfg)
        win.show()
    except Exception:
        sys.excepthook(*sys.exc_info())
        return
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
