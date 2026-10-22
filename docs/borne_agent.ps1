# Agent borne a beton Distri Beton <-> relais (Xavier, 22/10/2026).
# Tourne sur un PC du reseau de Chatel (qui voit le PC de la borne 192.168.1.200 et internet), lance a l'ouverture de session par
# borne_installer.ps1. Toutes les minutes :
#   1. clients : si un client Distri Beton a change dans Odoo (signature renvoyee par le relais), recupere le fichier complet
#      (format export Odoo) et le depose sur le FTP de la borne sous /Imports/Contact (res.partner).csv (fichier temporaire puis
#      renommage, la borne relit le fichier des qu'il change), puis consigne le resultat dans Odoo (historique sur la page /borne) ;
#   2. prises : lit les BLS*.csv de /Exports, les transmet au relais (page /borne : validation avant import), puis les range dans
#      /Exports/Sauv.
# Configuration : %LOCALAPPDATA%\BorneDistriBeton\config.json (mot de passe FTP chiffre DPAPI pour cette session Windows).
# Journal : %LOCALAPPDATA%\BorneDistriBeton\journal.txt. Etat : etat.json (derniere signature, dernier fichier depose).
param([string]$Config = (Join-Path $env:LOCALAPPDATA 'BorneDistriBeton\config.json'), [switch]$UneFois)
$ErrorActionPreference = 'Continue'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$dossier = Split-Path $Config -Parent
$journal = Join-Path $dossier 'journal.txt'; $etatFichier = Join-Path $dossier 'etat.json'
function Log([string]$m) { $l = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $m"; Write-Host $l; try { Add-Content -Path $journal -Value $l -Encoding UTF8 } catch {} }
if (-not (Test-Path $Config)) { Log "configuration absente : $Config (lancer borne_installer.ps1)"; exit 1 }
$cfg = Get-Content $Config -Raw -Encoding UTF8 | ConvertFrom-Json
$sec = ConvertTo-SecureString $cfg.ftp_pass_chiffre
$ftpPass = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec))
$cred = New-Object System.Net.NetworkCredential($cfg.ftp_user, $ftpPass)
$poste = if ($cfg.poste) { $cfg.poste } else { $env:COMPUTERNAME }
$intervalle = if ($cfg.intervalle) { [int]$cfg.intervalle } else { 60 }
$q = "k=$([uri]::EscapeDataString($cfg.cle))&poste=$([uri]::EscapeDataString($poste))"
$etat = @{ signature = ''; sha = ''; refus = '' }
if (Test-Path $etatFichier) { try { $e = Get-Content $etatFichier -Raw -Encoding UTF8 | ConvertFrom-Json; $etat.signature = [string]$e.signature; $etat.sha = [string]$e.sha; $etat.refus = [string]$e.refus } catch {} }
function SauverEtat { try { $etat | ConvertTo-Json | Out-File -FilePath $etatFichier -Encoding UTF8 } catch {} }

# ─── certificat du serveur FTP : empreinte SHA-256 epinglee dans la configuration (sinon acceptee et journalisee une fois)
$script:empreinteVue = ''
[Net.ServicePointManager]::ServerCertificateValidationCallback = {
  param($sender, $cert, $chain, $erreurs)
  $sha = [BitConverter]::ToString([Security.Cryptography.SHA256]::Create().ComputeHash($cert.GetRawCertData())).Replace('-', '').ToLower()
  if ($cfg.empreinte) { return ($sha -eq $cfg.empreinte.ToLower()) }
  if ($script:empreinteVue -ne $sha) { $script:empreinteVue = $sha; Log "certificat FTP accepte sans epinglage, empreinte $sha (a reporter dans config.json : empreinte)" }
  return $true
}

# ─── FTP (FileZilla Server : TLS explicite obligatoire)
function FtpReq([string]$chemin, [string]$methode) {
  $r = [Net.FtpWebRequest]::Create("ftp://$($cfg.ftp_host)$chemin"); $r.EnableSsl = $true; $r.UsePassive = $true; $r.UseBinary = $true; $r.KeepAlive = $false
  $r.Credentials = $cred; $r.Method = $methode; $r.Timeout = 20000; $r.ReadWriteTimeout = 20000; return $r
}
function FtpListe([string]$dossierFtp) {
  $r = FtpReq "$dossierFtp/" ([Net.WebRequestMethods+Ftp]::ListDirectory); $resp = $r.GetResponse()
  $sr = New-Object IO.StreamReader($resp.GetResponseStream()); $txt = $sr.ReadToEnd(); $sr.Close(); $resp.Close()
  return @($txt -split "`r?`n" | ForEach-Object { $_.Trim() } | Where-Object { $_ } | ForEach-Object { Split-Path $_ -Leaf })
}
function FtpLire([string]$chemin) {
  $r = FtpReq $chemin ([Net.WebRequestMethods+Ftp]::DownloadFile); $resp = $r.GetResponse(); $ms = New-Object IO.MemoryStream
  $resp.GetResponseStream().CopyTo($ms); $resp.Close(); return $ms.ToArray()
}
function FtpEcrire([string]$chemin, [byte[]]$octets) {
  $r = FtpReq $chemin ([Net.WebRequestMethods+Ftp]::UploadFile); $r.ContentLength = $octets.Length
  $s = $r.GetRequestStream(); $s.Write($octets, 0, $octets.Length); $s.Close(); $resp = $r.GetResponse(); $resp.Close()
}
function FtpSupprimer([string]$chemin) { try { $r = FtpReq $chemin ([Net.WebRequestMethods+Ftp]::DeleteFile); $resp = $r.GetResponse(); $resp.Close(); return $true } catch { return $false } }
function FtpRenommer([string]$chemin, [string]$nouveau) {
  $r = FtpReq $chemin ([Net.WebRequestMethods+Ftp]::Rename); $r.RenameTo = $nouveau; $resp = $r.GetResponse(); $resp.Close()
}

# ─── relais
function EnTete($rep, [string]$nom) {
  # les en-tetes reviennent en minuscules derriere le proxy de Render
  foreach ($k in $rep.Headers.Keys) { if ($k -ieq $nom) { return [string]$rep.Headers[$k] } }
  return ''
}
function Relais([string]$chemin, $corps) {
  $sep = if ($chemin.Contains('?')) { '&' } else { '?' }; $url = "$($cfg.url)/borne/api/$chemin$sep$q"
  if ($null -ne $corps) {
    $json = [Text.Encoding]::UTF8.GetBytes((ConvertTo-Json $corps -Depth 5 -Compress))
    return Invoke-RestMethod -Method Post -Uri $url -ContentType 'application/json; charset=utf-8' -Body $json -TimeoutSec 120
  }
  return Invoke-RestMethod -Method Get -Uri $url -TimeoutSec 60
}
function Journal([string]$resultat, [int]$nb, [int]$nouveaux, $liste, [string]$sha, [string]$detail) {
  try { Relais 'export-journal' @{ resultat = $resultat; nb_clients = $nb; nb_nouveaux = $nouveaux; nouveaux = @($liste); sha = $sha; detail = $detail; poste = $poste } | Out-Null }
  catch { Log "journal : $($_.Exception.Message)" }
}

# ─── 1. clients Odoo -> borne
function Clients($info) {
  $sig = [string]$info.clients.sig; $forcer = [bool]$info.forcer
  if ($sig -eq $etat.signature -and -not $forcer) { return }
  $url = "$($cfg.url)/borne/api/clients.csv?$q" + $(if ($forcer) { '&forcer=1' } else { '' })
  try { $rep = Invoke-WebRequest -Uri $url -TimeoutSec 120 -UseBasicParsing }
  catch {
    $r = $_.Exception.Response
    if ($r -and [int]$r.StatusCode -eq 409) {
      $sr = New-Object IO.StreamReader($r.GetResponseStream()); $j = $sr.ReadToEnd() | ConvertFrom-Json; $sr.Close()
      $motifs = ($j.motifs -join ' ; ')
      if ($etat.refus -ne "$sig|$motifs") { Log "depot clients refuse par le relais : $motifs"; Journal 'refuse' ([int]$j.nb) 0 @() '' $motifs; $etat.refus = "$sig|$motifs"; SauverEtat }
      return
    }
    Log "clients.csv : $($_.Exception.Message)"; return
  }
  $octets = $rep.Content; if ($octets -isnot [byte[]]) { $octets = [Text.Encoding]::UTF8.GetBytes([string]$octets) }
  $sha = EnTete $rep 'X-Sha'; $nb = [int](EnTete $rep 'X-Nb-Clients'); $nbNouveaux = [int](EnTete $rep 'X-Nb-Nouveaux')
  $nouveaux = @(); try { $nouveaux = @(((EnTete $rep 'X-Nouveaux') | ConvertFrom-Json)) } catch {}
  $fichier = EnTete $rep 'X-Fichier'; if (-not $fichier) { $fichier = 'Contact (res.partner).csv' }
  if ($sha -eq $etat.sha -and -not $forcer) {
    $etat.signature = $sig; SauverEtat
    Journal 'inchange' $nb 0 @() $sha 'fichier identique au dernier depot'; return
  }
  $cible = "$($cfg.dossier_imports)/$fichier"; $tmp = "$($cfg.dossier_imports)/$fichier.tmp"
  try {
    FtpEcrire $tmp $octets
    FtpSupprimer $cible | Out-Null
    try { FtpRenommer $tmp $cible } catch { Log "renommage impossible ($($_.Exception.Message)), ecriture directe"; FtpEcrire $cible $octets; FtpSupprimer $tmp | Out-Null }
    $etat.signature = $sig; $etat.sha = $sha; $etat.refus = ''; SauverEtat
    Log "fichier clients depose sur la borne : $nb clients, $nbNouveaux nouveau(x)/modifie(s)$(if ($forcer) { ' (force)' })"
    Journal 'depose' $nb $nbNouveaux $nouveaux $sha "$cible, $($octets.Length) octets$(if ($forcer) { ', depot force' })"
  } catch {
    Log "depot FTP : $($_.Exception.Message)"
    Journal 'erreur' $nb $nbNouveaux $nouveaux $sha "depot FTP impossible : $($_.Exception.Message)"
  }
}

# ─── 2. prises de beton (BLS*.csv) -> relais
function Prises {
  try { $noms = @(FtpListe $cfg.dossier_exports | Where-Object { $_ -match '^BLS\d+\.csv$' } | Sort-Object) } catch { Log "liste FTP : $($_.Exception.Message)"; return }
  if (-not $noms.Count) { return }
  $lot = @()
  foreach ($n in ($noms | Select-Object -First 100)) {
    try { $lot += @{ nom = $n; contenu = [Text.Encoding]::UTF8.GetString((FtpLire "$($cfg.dossier_exports)/$n")) } }
    catch { Log "lecture $n : $($_.Exception.Message)" }
  }
  if (-not $lot.Count) { return }
  try { $rep = Relais 'depot' @{ fichiers = $lot; poste = $poste } } catch { Log "depot relais : $($_.Exception.Message)"; return }
  $crees = 0; $deja = 0
  foreach ($f in $lot) {
    $res = [string]$rep.resultats.($f.nom)
    if ($res -eq 'cree' -or $res -eq 'deja') {
      if ($res -eq 'cree') { $crees++ } else { $deja++ }
      try { FtpRenommer "$($cfg.dossier_exports)/$($f.nom)" "$($cfg.dossier_sauv)/$($f.nom)" } catch { Log "archivage $($f.nom) : $($_.Exception.Message)" }
    } else { Log "$($f.nom) : $res" }
  }
  Log "prises : $($lot.Count) fichier(s) lu(s), $crees transmis, $deja deja connu(s)"
}

Log "demarrage : relais $($cfg.url), borne $($cfg.ftp_host) ($($cfg.ftp_user)), poste $poste, toutes les $intervalle s"
while ($true) {
  $t0 = Get-Date
  try {
    $info = Relais "etat?agent=1"
    Clients $info
    Prises
  } catch { Log "cycle : $($_.Exception.Message)" }
  if ($UneFois) { break }
  $reste = $intervalle - ((Get-Date) - $t0).TotalSeconds
  if ($reste -gt 0) { Start-Sleep -Seconds ([int]$reste) }
}
