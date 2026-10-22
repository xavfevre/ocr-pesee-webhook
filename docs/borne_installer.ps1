# Borne Distri Beton - installation de l'agent sur un PC du reseau de Chatel (PowerShell, sans droits administrateur) :
#   powershell -ExecutionPolicy Bypass -File borne_installer.ps1
#   (la cle de la page et le mot de passe FTP sont demandes ; parametres facultatifs : -Cle, -FtpUser, -FtpPass, -FtpHost 192.168.1.200,
#    -Empreinte <sha256 du certificat FTP>, -Poste caisse-chatel, -Url https://ocr-pesee-webhook.onrender.com)
# A lancer DANS LA SESSION WINDOWS qui restera ouverte (le mot de passe FTP est chiffre pour cette session uniquement).
# Copie l'agent dans %LOCALAPPDATA%\BorneDistriBeton, ecrit sa configuration, cree le raccourci de demarrage automatique
# a l'ouverture de session et lance l'agent tout de suite.
param(
    [string]$Cle = '',
    [string]$FtpUser = 'contact@chatelbeton.fr',
    [string]$FtpPass = '',
    [string]$FtpHost = '192.168.1.200',
    [string]$Empreinte = 'ab1d8099829d8f0035f151de37b84fdd2d915569e8947a32f561cc2594134393',
    [string]$Poste = $env:COMPUTERNAME,
    [string]$Url = 'https://ocr-pesee-webhook.onrender.com',
    [int]$Intervalle = 60
)
$ErrorActionPreference = 'Stop'
# sans parametres : les valeurs sont demandees (rien a taper dans la commande)
if (-not $Cle) { $Cle = (Read-Host 'Cle de la page borne (Odoo > Logistiques > Borne a beton > Page de validation : ce qui suit k= dans l adresse)').Trim() }
if (-not $FtpPass) { $FtpPass = Read-Host "Mot de passe FTP de la borne (compte $FtpUser)" }
if (-not $Cle -or -not $FtpPass) { Write-Host 'Cle ou mot de passe manquant : abandon.'; exit 1 }
$prog = Join-Path $env:LOCALAPPDATA 'BorneDistriBeton'
New-Item -ItemType Directory -Force -Path $prog | Out-Null
Copy-Item -Path (Join-Path $PSScriptRoot 'borne_agent.ps1') -Destination $prog -Force
$chiffre = ConvertTo-SecureString $FtpPass -AsPlainText -Force | ConvertFrom-SecureString
@{ url = $Url; cle = $Cle; poste = $Poste; intervalle = $Intervalle; ftp_host = $FtpHost; ftp_user = $FtpUser; ftp_pass_chiffre = $chiffre; empreinte = $Empreinte
   dossier_exports = '/Exports'; dossier_sauv = '/Exports/Sauv'; dossier_imports = '/Imports' } | ConvertTo-Json | Out-File -FilePath (Join-Path $prog 'config.json') -Encoding UTF8
$lnk = Join-Path ([Environment]::GetFolderPath('Startup')) 'Borne Distri Beton.lnk'
$ws = New-Object -ComObject WScript.Shell
$rac = $ws.CreateShortcut($lnk)
$rac.TargetPath = 'powershell.exe'
$rac.Arguments = '-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "' + (Join-Path $prog 'borne_agent.ps1') + '"'
$rac.WorkingDirectory = $prog
$rac.Description = 'Borne Distri Beton : clients Odoo vers la borne, prises de beton vers Odoo'
$rac.Save()
Get-CimInstance Win32_Process -Filter "Name = 'powershell.exe'" | Where-Object { $_.CommandLine -like '*borne_agent.ps1*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Start-Process -FilePath 'powershell.exe' -ArgumentList $rac.Arguments -WorkingDirectory $prog -WindowStyle Hidden
Write-Host ''
Write-Host "Agent installe dans $prog et demarre (il repartira seul a chaque ouverture de session)."
Write-Host "Borne : $FtpHost (compte $FtpUser)   Relais : $Url   Poste : $Poste"
Write-Host "Journal : $prog\journal.txt   Page de validation : $Url/borne/?k=<cle>"
