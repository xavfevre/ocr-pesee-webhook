@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Passerelle cameras Chatel (enregistreur Dahua 192.168.1.208) : les deux vues partent vers la page Pont-bascule.
echo Le fichier bascule_passerelle.ps1 doit etre dans le meme dossier que ce lanceur. Laisser la fenetre ouverte.
echo.
set /p CLE=Cle d acces de la page Pont-bascule (ce qui suit k= dans l adresse du menu Logistiques, Pont-bascule Chatel) : 
set /p MDP=Mot de passe camera (compte delphine) : 
powershell -NoExit -ExecutionPolicy Bypass -File "%~dp0bascule_passerelle.ps1" -Site chatel -Port "" -Cle "%CLE%" -Camera "http://192.168.1.208/cgi-bin/snapshot.cgi?channel=1" -Camera2 "http://192.168.1.208/cgi-bin/snapshot.cgi?channel=2" -CamUser delphine -CamPwd "%MDP%"
