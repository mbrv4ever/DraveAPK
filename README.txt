DraveAPK - bouw je Python/Kivy-app naar Android, met knoppen (Dravenlock)
========================================================================

Wat is het?
-----------
DraveAPK maakt van je Python/Kivy-app een Android-bestand (.apk) zonder dat je
zelf in een zwart commandovenster hoeft te typen. Het zware werk gebeurt in
WSL2 + Buildozer (dat je eenmalig opzet); DraveAPK stuurt dat aan en toont de
voortgang in een net venster.

Eenmalig vooraf
---------------
- Windows met WSL2 + Ubuntu, en daarin Buildozer geinstalleerd.
- Heb je dat nog niet? Volg deze stappen:

WSL + Buildozer installeren (eenmalig, ongeveer een half uur)
  1. Open PowerShell als administrator en typ:
       wsl --install -d Ubuntu-22.04
     Start de pc opnieuw op en kies een gebruikersnaam en wachtwoord voor Ubuntu.
  2. Open 'Ubuntu' via het startmenu en typ (een regel tegelijk):
       sudo apt update
       sudo apt install -y git zip unzip openjdk-17-jdk python3-pip autoconf libtool pkg-config zlib1g-dev libncurses5-dev libffi-dev libssl-dev cmake
       pip3 install --user buildozer cython
       echo 'export PATH=$PATH:~/.local/bin' >> ~/.profile
  3. Sluit Ubuntu, start DraveAPK en klik op 'Controleer omgeving'.

- Start DraveAPK en klik op "Controleer omgeving". Groen = klaar.

Een APK bouwen
--------------
1. "Bladeren..." -> kies je projectmap (de map met main.py).
2. Vul een App-naam in (de pakketnaam wordt automatisch voorgesteld).
3. "Vereisten" = wat je app nodig heeft (standaard: python3,kivy).
4. Klik "Bouw APK". De eerste keer duurt lang (Buildozer haalt de Android-
   gereedschappen op). Volg de voortgang in het venster.
5. Klaar? De .apk staat in een "bin"-map in je project. Zet die op je telefoon,
   sta "installeren van onbekende bronnen" toe en open de app.

Goed om te weten
----------------
- Heeft je project al een buildozer.spec, dan gebruikt DraveAPK die. Anders maakt
  hij er zelf eentje aan met je naam/pakketnaam/vereisten.
- DraveAPK kopieert je project naar de Linux-kant en bouwt daar (dat is sneller en
  betrouwbaarder dan bouwen vanaf de Windows-schijf).
- Android-apps maak je het best in Kivy (touch). Gewone PyQt-apps gaan niet zomaar
  mee naar Android.

Starten / EXE
-------------
- Starten: dubbelklik run.bat.
- EXE maken: bouw-exe.bat -> dist\DraveAPK\DraveAPK.exe.

Instellingen (draveapk_config.json)
-----------------------------------
  "distro"        : naam van je WSL-distributie (standaard Ubuntu-22.04)
  "domain"        : pakket-domein (standaard nl.dravenlock)
  "project"       : laatst gekozen projectmap
  "requirements"  : standaard vereisten

Werkt iets niet?
----------------
- "Kon WSL niet starten": WSL2/Ubuntu ontbreekt -> zie de stappen bovenaan.
- "Buildozer NIET GEVONDEN" bij Controleer omgeving: stap 2 van SETUP nog doen.
- Bouwfout: stuur de laatste rode/Engelse regels uit het log door.
