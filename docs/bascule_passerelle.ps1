# Passerelle pont-bascule -> relais (Maquignon, 21/10/2026).
# Lit l'indicateur Bilanciai (commande XB) sur le port serie et envoie le poids au relais chaque seconde, plus l'image de la
# camera du pont toutes les 2 s. Tourne sur le PC de la cabine (celui qui tient le cable serie), lance au demarrage de Windows.
# La page Pont-bascule ouverte sur n'importe quel autre PC (accueil) affiche alors le poids et l'image comme si la bascule etait branchee dessus.
#
# Usage : powershell -ExecutionPolicy Bypass -File bascule_passerelle.ps1 -Site maquignon -Port COM1 [-Cle <cle maquignon.bascule_key>]
#         [-Camera http://192.168.1.60/cgi-bin/snapshot.cgi -CamUser admin -CamPwd xxxx] [-Intervalle 1] [-ImageIntervalle 2]
#         [-Camera2 http://.../snapshot.cgi?channel=2 -Image2Intervalle 6] (seconde vue, memes identifiants ; les images de plus de 250 Ko
#         sont reduites a -ImageLargeurMax 1280 px avant envoi)
# Chatel (enregistreur Dahua XVR 192.168.1.208, PC de caisse, bascule lue par le cable USB) :
#   -Site chatel -Port '' -Camera "http://192.168.1.208/cgi-bin/snapshot.cgi?channel=1" -Camera2 "http://192.168.1.208/cgi-bin/snapshot.cgi?channel=2" -CamUser delphine -CamPwd xxxx
# La cle peut aussi etre dans un fichier bascule_cle.txt a cote du script (une ligne).
# Lancement automatique (une fois, en administrateur) :
#   schtasks /Create /F /SC ONLOGON /RL HIGHEST /TN "Passerelle bascule" /TR "powershell -ExecutionPolicy Bypass -WindowStyle Hidden -File C:\Maquignon\bascule_passerelle.ps1 -Site maquignon -Port COM1"
# Journal : %TEMP%\bascule_passerelle.log
# Camera seule (la page lit la bascule par le cable USB, ex. PC de caisse de Chatel) : -Port '' -Site chatel -Camera http://...
param([string]$Site = 'maquignon', [string]$Port = 'COM1', [int]$Baud = 9600, [string]$Cle = '', [string]$Relais = 'https://ocr-pesee-webhook.onrender.com',
      [string]$Camera = '', [string]$CamUser = '', [string]$CamPwd = '', [double]$Intervalle = 1.0, [double]$ImageIntervalle = 2.0, [string]$Poste = $env:COMPUTERNAME,
      [string]$Camera2 = '', [double]$Image2Intervalle = 6.0, [int]$ImageLargeurMax = 1280)
$ErrorActionPreference = 'Continue'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
if (-not $Cle) { $f = Join-Path $PSScriptRoot 'bascule_cle.txt'; if (Test-Path $f) { $Cle = (Get-Content $f | Select-Object -First 1).Trim() } }
if (-not $Cle) { Write-Host 'Cle manquante : parametre -Cle ou fichier bascule_cle.txt a cote du script.'; exit 1 }
$q = "site=$Site&k=$([uri]::EscapeDataString($Cle))"
$urlPoids = "$Relais/bascule/api/passerelle?$q"; $urlImage = "$Relais/bascule/api/passerelle/image?$q"; $urlImage2 = "$Relais/bascule/api/passerelle/image?$q&n=2"
$journal = Join-Path $env:TEMP 'bascule_passerelle.log'
function Log([string]$m) { $l = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $m"; Write-Host $l; try { Add-Content -Path $journal -Value $l } catch {} }
function Envoyer($obj) {
  try { Invoke-RestMethod -Method Post -Uri $urlPoids -ContentType 'application/json; charset=utf-8' -Body ([Text.Encoding]::UTF8.GetBytes((ConvertTo-Json $obj -Compress))) -TimeoutSec 5 | Out-Null; return $true }
  catch { Log "relais : $($_.Exception.Message)"; return $false }
}
$cred = $null
if ($CamUser) { $cred = New-Object System.Management.Automation.PSCredential($CamUser, (ConvertTo-SecureString $CamPwd -AsPlainText -Force)) }
Add-Type -AssemblyName System.Drawing
function Reduire([byte[]]$octets, [int]$largeurMax) {
  # image 4K de l'enregistreur (~900 Ko) : reduite avant envoi pour menager la ligne internet du site
  if ($octets.Length -lt 250000 -or $largeurMax -le 0) { return $octets }
  try {
    $ms = New-Object IO.MemoryStream(,$octets); $bmp = [Drawing.Image]::FromStream($ms)
    if ($bmp.Width -le $largeurMax) { $bmp.Dispose(); $ms.Dispose(); return $octets }
    $h = [int]($bmp.Height * $largeurMax / $bmp.Width); $petit = New-Object Drawing.Bitmap $largeurMax, $h
    $g = [Drawing.Graphics]::FromImage($petit); $g.InterpolationMode = 'HighQualityBicubic'; $g.DrawImage($bmp, 0, 0, $largeurMax, $h); $g.Dispose()
    $codec = [Drawing.Imaging.ImageCodecInfo]::GetImageEncoders() | Where-Object { $_.MimeType -eq 'image/jpeg' }
    $prm = New-Object Drawing.Imaging.EncoderParameters 1; $prm.Param[0] = New-Object Drawing.Imaging.EncoderParameter([Drawing.Imaging.Encoder]::Quality, [long]75)
    $out = New-Object IO.MemoryStream; $petit.Save($out, $codec, $prm); $res = $out.ToArray()
    $petit.Dispose(); $bmp.Dispose(); $ms.Dispose(); $out.Dispose(); return $res
  } catch { Log "reduction image : $($_.Exception.Message)"; return $octets }
}
function EnvoyerImage([string]$source, [string]$cible) {
  if ($cred) { $img = Invoke-WebRequest -Uri $source -Credential $cred -TimeoutSec 8 -UseBasicParsing } else { $img = Invoke-WebRequest -Uri $source -TimeoutSec 8 -UseBasicParsing }
  $octets = Reduire ([byte[]]$img.Content) $ImageLargeurMax
  Invoke-RestMethod -Method Post -Uri $cible -ContentType 'image/jpeg' -Body $octets -TimeoutSec 8 | Out-Null
}
$derniers = New-Object System.Collections.ArrayList
$p = $null; $derniereImage = [datetime]::MinValue; $derniereImage2 = [datetime]::MinValue; $nbEnvois = 0; $nbErreurs = 0
Log "demarrage : site $Site, port $(if ($Port) { $Port } else { 'aucun (camera seule)' }) a $Baud bauds, relais $Relais, camera $(if ($Camera) { $Camera } else { 'aucune' }), camera 2 $(if ($Camera2) { $Camera2 } else { 'aucune' }), poste $Poste"
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
    try { EnvoyerImage $Camera $urlImage; $derniereImage = Get-Date }
    catch { Log "camera : $($_.Exception.Message)"; $derniereImage = (Get-Date).AddSeconds(15) }
  }
  if ($Camera2 -and ((Get-Date) - $derniereImage2).TotalSeconds -ge $Image2Intervalle) {
    try { EnvoyerImage $Camera2 $urlImage2; $derniereImage2 = Get-Date }
    catch { Log "camera 2 : $($_.Exception.Message)"; $derniereImage2 = (Get-Date).AddSeconds(15) }
  }
  $reste = $Intervalle - ((Get-Date) - $t0).TotalSeconds
  if ($reste -gt 0) { Start-Sleep -Milliseconds ([int]($reste * 1000)) }
}
