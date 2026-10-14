# Scan Odoo - installation du veilleur sur le PC (à lancer dans PowerShell, sans droits administrateur) :
#   powershell -ExecutionPolicy Bypass -File installer.ps1 -Cle <clé maquignon.scan_key> [-Poste isabelle] [-Dossier "C:\...\Scan Odoo"]
# Copie le veilleur dans %LOCALAPPDATA%\ScanOdoo, écrit sa configuration, crée le raccourci de démarrage
# automatique à l'ouverture de session et lance le veilleur tout de suite.
# Ensuite : dans Brother iPrint&Scan, régler « Numériser vers fichier » en PDF vers le dossier indiqué.
param(
    [Parameter(Mandatory = $true)][string]$Cle,
    [string]$Poste = 'isabelle',
    [string]$Url = 'https://ocr-pesee-webhook.onrender.com',
    [string]$Dossier = (Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'Scan Odoo')
)
$ErrorActionPreference = 'Stop'
$prog = Join-Path $env:LOCALAPPDATA 'ScanOdoo'
New-Item -ItemType Directory -Force -Path $prog, $Dossier, (Join-Path $Dossier 'Envoyés') | Out-Null
Copy-Item -Path (Join-Path $PSScriptRoot 'scan_odoo_veilleur.ps1') -Destination $prog -Force
@{ url = $Url; cle = $Cle; poste = $Poste.ToLower(); dossier = $Dossier } | ConvertTo-Json | Out-File -FilePath (Join-Path $prog 'config.json') -Encoding UTF8
$demarrage = [Environment]::GetFolderPath('Startup')
$lnk = Join-Path $demarrage 'Scan Odoo.lnk'
$ws = New-Object -ComObject WScript.Shell
$rac = $ws.CreateShortcut($lnk)
$rac.TargetPath = 'powershell.exe'
$rac.Arguments = '-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "' + (Join-Path $prog 'scan_odoo_veilleur.ps1') + '"'
$rac.WorkingDirectory = $prog
$rac.Description = 'Scan Odoo : envoie les scans du dossier Scan Odoo dans les fiches véhicules'
$rac.Save()
Get-CimInstance Win32_Process -Filter "Name = 'powershell.exe'" | Where-Object { $_.CommandLine -like '*scan_odoo_veilleur.ps1*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Start-Process -FilePath 'powershell.exe' -ArgumentList $rac.Arguments -WorkingDirectory $prog -WindowStyle Hidden
Write-Host ''
Write-Host "Veilleur installé dans $prog et démarré (il repartira seul à chaque ouverture de session)."
Write-Host "Poste : $($Poste.ToLower())   Dossier à surveiller : $Dossier"
Write-Host 'Dans Brother iPrint&Scan : « Paramètres de Numérisation Appareil » (ou le bouton Numériser), fonction Fichier,'
Write-Host "type PDF, recto-verso, dossier de destination = $Dossier"
Write-Host "Journal : $prog\journal.txt"
