# Scan Odoo - veilleur du poste (14/10/2026)
# Surveille le dossier où iPrint&Scan enregistre les scans (PDF/JPG) et envoie chaque nouveau fichier au relais
# Render, qui l'attache au véhicule affiché sur la page « Scanner dans Odoo » de ce poste.
# Fichier envoyé -> déplacé dans le sous-dossier « Envoyés ». Journal : journal.txt à côté de ce script.
# Lancé à l'ouverture de session par le raccourci créé par installer.ps1 (powershell -WindowStyle Hidden ...).
param([string]$Config = (Join-Path $PSScriptRoot 'config.json'))
$ErrorActionPreference = 'Continue'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$c = Get-Content -Path $Config -Raw -Encoding UTF8 | ConvertFrom-Json
$journal = Join-Path $PSScriptRoot 'journal.txt'
function Log([string]$m) { Add-Content -Path $journal -Value ("{0:yyyy-MM-dd HH:mm:ss} {1}" -f (Get-Date), $m) -Encoding UTF8 }
$icone = $null
try {
    Add-Type -AssemblyName System.Windows.Forms, System.Drawing
    $icone = New-Object System.Windows.Forms.NotifyIcon
    $icone.Icon = [System.Drawing.SystemIcons]::Information; $icone.Text = 'Scan Odoo : veilleur actif'; $icone.Visible = $true
} catch { }
function Bulle([string]$titre, [string]$texte, [string]$genre = 'Info') {
    if ($icone) { try { $icone.ShowBalloonTip(5000, $titre, $texte, $genre); [System.Windows.Forms.Application]::DoEvents() } catch { } }
}
$dossier = [Environment]::ExpandEnvironmentVariables($c.dossier)
$envoyes = Join-Path $dossier 'Envoyés'
New-Item -ItemType Directory -Force -Path $dossier, $envoyes | Out-Null
Log "démarrage : dossier $dossier, poste $($c.poste), relais $($c.url)"
Bulle 'Scan Odoo' "Veilleur actif : les scans déposés dans $dossier partent dans Odoo."
$attente = @{}
while ($true) {
    $fichiers = Get-ChildItem -Path $dossier -File -ErrorAction SilentlyContinue | Where-Object { $_.Extension -match '^\.(pdf|jpg|jpeg|png|tif|tiff)$' -and $_.LastWriteTime -lt (Get-Date).AddSeconds(-3) -and $_.Length -gt 100 }
    foreach ($f in $fichiers) {
        if ($attente.ContainsKey($f.FullName) -and $attente[$f.FullName] -gt (Get-Date)) { continue }   # échec récent : on réessaie plus tard
        try { $s = [IO.File]::Open($f.FullName, 'Open', 'Read', 'None'); $s.Close() } catch { continue }   # encore en cours d'écriture par le scanner
        try {
            $url = '{0}/scan-vehicule/api/upload?k={1}&poste={2}&nom={3}' -f $c.url.TrimEnd('/'), [Uri]::EscapeDataString($c.cle), [Uri]::EscapeDataString($c.poste), [Uri]::EscapeDataString($f.Name)
            $r = Invoke-RestMethod -Uri $url -Method Post -InFile $f.FullName -ContentType 'application/octet-stream' -TimeoutSec 180
            if ($r.ok) {
                $dest = Join-Path $envoyes $f.Name
                if (Test-Path $dest) { $dest = Join-Path $envoyes ("{0}_{1:yyyyMMdd_HHmmss}{2}" -f $f.BaseName, (Get-Date), $f.Extension) }
                Move-Item -Path $f.FullName -Destination $dest -Force
                Log "envoyé $($f.Name) -> $($r.message)"
                if ($r.veh) { Bulle 'Scan Odoo' $r.message } else { Bulle 'Scan Odoo : à classer' $r.message 'Warning' }
                $attente.Remove($f.FullName)
            } else {
                Log "refusé $($f.Name) : $($r.error)"; Bulle 'Scan Odoo : refusé' "$($f.Name) : $($r.error)" 'Error'
                $attente[$f.FullName] = (Get-Date).AddSeconds(60)
            }
        } catch {
            $msg = $_.Exception.Message
            Log "erreur $($f.Name) : $msg"; Bulle 'Scan Odoo : erreur' "$($f.Name) : $msg (nouvel essai dans 1 min)" 'Error'
            $attente[$f.FullName] = (Get-Date).AddSeconds(60)
        }
    }
    Start-Sleep -Seconds 2
}
