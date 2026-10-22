# Passerelle pont-bascule -> relais (Maquignon, 21/10/2026).
# Lit l'indicateur Bilanciai (commande XB) sur le port serie et envoie le poids au relais chaque seconde, plus l'image de la
# camera du pont toutes les 2 s. Tourne sur le PC de la cabine (celui qui tient le cable serie), lance au demarrage de Windows.
# La page Pont-bascule ouverte sur n'importe quel autre PC (accueil) affiche alors le poids et l'image comme si la bascule etait branchee dessus.
#
# Usage : powershell -ExecutionPolicy Bypass -File bascule_passerelle.ps1 -Site maquignon -Port COM1 [-Cle <cle maquignon.bascule_key>]
#         [-Camera http://192.168.1.60/cgi-bin/snapshot.cgi -CamUser admin -CamPwd xxxx] [-Intervalle 1] [-ImageIntervalle 2]
# La cle peut aussi etre dans un fichier bascule_cle.txt a cote du script (une ligne).
# Lancement automatique (une fois, en administrateur) :
#   schtasks /Create /F /SC ONLOGON /RL HIGHEST /TN "Passerelle bascule" /TR "powershell -ExecutionPolicy Bypass -WindowStyle Hidden -File C:\Maquignon\bascule_passerelle.ps1 -Site maquignon -Port COM1"
# Journal : %TEMP%\bascule_passerelle.log
# Camera seule (la page lit la bascule par le cable USB, ex. PC de caisse de Chatel) : -Port '' -Site chatel -Camera http://...
param([string]$Site = 'maquignon', [string]$Port = 'COM1', [int]$Baud = 9600, [string]$Cle = '', [string]$Relais = 'https://ocr-pesee-webhook.onrender.com',
      [string]$Camera = '', [string]$CamUser = '', [string]$CamPwd = '', [double]$Intervalle = 1.0, [double]$ImageIntervalle = 2.0, [string]$Poste = $env:COMPUTERNAME)
$ErrorActionPreference = 'Continue'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
if (-not $Cle) { $f = Join-Path $PSScriptRoot 'bascule_cle.txt'; if (Test-Path $f) { $Cle = (Get-Content $f | Select-Object -First 1).Trim() } }
if (-not $Cle) { Write-Host 'Cle manquante : parametre -Cle ou fichier bascule_cle.txt a cote du script.'; exit 1 }
$q = "site=$Site&k=$([uri]::EscapeDataString($Cle))"
$urlPoids = "$Relais/bascule/api/passerelle?$q"; $urlImage = "$Relais/bascule/api/passerelle/image?$q"
$journal = Join-Path $env:TEMP 'bascule_passerelle.log'
function Log([string]$m) { $l = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $m"; Write-Host $l; try { Add-Content -Path $journal -Value $l } catch {} }
function Envoyer($obj) {
  try { Invoke-RestMethod -Method Post -Uri $urlPoids -ContentType 'application/json; charset=utf-8' -Body ([Text.Encoding]::UTF8.GetBytes((ConvertTo-Json $obj -Compress))) -TimeoutSec 5 | Out-Null; return $true }
  catch { Log "relais : $($_.Exception.Message)"; return $false }
}
$cred = $null
if ($CamUser) { $cred = New-Object System.Management.Automation.PSCredential($CamUser, (ConvertTo-SecureString $CamPwd -AsPlainText -Force)) }
$derniers = New-Object System.Collections.ArrayList
$p = $null; $derniereImage = [datetime]::MinValue; $nbEnvois = 0; $nbErreurs = 0
Log "demarrage : site $Site, port $(if ($Port) { $Port } else { 'aucun (camera seule)' }) a $Baud bauds, relais $Relais, camera $(if ($Camera) { $Camera } else { 'aucune' }), poste $Poste"
while ($true) {
  $t0 = Get-Date
  if ($Port) { try {
    if (-not $p -or -not $p.IsOpen) {
      $p = New-Object System.IO.Ports.SerialPort $Port, $Baud, 'None', 8, 'One'
      $p.ReadTimeout = 800; $p.NewLine = "`n"; $p.Encoding = [Text.Encoding]::GetEncoding(28591)
      $p.Open(); $derniers.Clear(); Log "port $Port ouvert"
    }
    $p.DiscardInBuffer(); $p.Write("XB`r")
    $rep = $p.ReadLine().Trim()
    $m = [regex]::Match($rep, '^\s*(-?\d+)\s*(kg|t)\s*([A-Z]*)', 'IgnoreCase')
    if ($m.Success) {
      $kg = [int]$m.Groups[1].Value; if ($m.Groups[2].Value -eq 't') { $kg = $kg * 1000 }
      [void]$derniers.Add($kg); while ($derniers.Count -gt 3) { $derniers.RemoveAt(0) }
      $stable = ($derniers.Count -eq 3) -and (($derniers | Select-Object -Unique).Count -eq 1)
      if (Envoyer @{ site = $Site; k = $Cle; poids = $kg; stable = $stable; etat = $m.Groups[3].Value; brut = $rep; poste = $Poste }) { $nbEnvois++ }
      if ($nbEnvois % 600 -eq 1) { Log "poids $kg kg ($rep), $nbEnvois envois, $nbErreurs erreurs" }
    } else {
      $nbErreurs++; Log "reponse illisible : '$rep'"
      Envoyer @{ site = $Site; k = $Cle; poids = $null; stable = $false; brut = $rep; erreur = "reponse illisible : $rep"; poste = $Poste } | Out-Null
    }
  } catch {
    $nbErreurs++; Log "bascule : $($_.Exception.Message)"
    Envoyer @{ site = $Site; k = $Cle; poids = $null; stable = $false; erreur = "port $Port : $($_.Exception.Message)"; poste = $Poste } | Out-Null
    try { if ($p) { $p.Close() } } catch {}
    $p = $null; Start-Sleep -Seconds 3
  } }
  if ($Camera -and ((Get-Date) - $derniereImage).TotalSeconds -ge $ImageIntervalle) {
    try {
      if ($cred) { $img = Invoke-WebRequest -Uri $Camera -Credential $cred -TimeoutSec 4 -UseBasicParsing } else { $img = Invoke-WebRequest -Uri $Camera -TimeoutSec 4 -UseBasicParsing }
      Invoke-RestMethod -Method Post -Uri $urlImage -ContentType 'image/jpeg' -Body $img.Content -TimeoutSec 5 | Out-Null
      $derniereImage = Get-Date
    } catch { Log "camera : $($_.Exception.Message)"; $derniereImage = (Get-Date).AddSeconds(15) }
  }
  $reste = $Intervalle - ((Get-Date) - $t0).TotalSeconds
  if ($reste -gt 0) { Start-Sleep -Milliseconds ([int]($reste * 1000)) }
}
