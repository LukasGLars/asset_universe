$ROOT    = "C:\Users\lukas.larsson\Desktop\asset_universe"
$LOG_DIR = "$ROOT\logs"
$DATE    = Get-Date -Format "yyyy-MM-dd"
$LOG     = "$LOG_DIR\$DATE.log"

if (-not (Test-Path $LOG_DIR)) { New-Item -ItemType Directory -Path $LOG_DIR | Out-Null }

"=== daily_sync $DATE $(Get-Date -Format 'HH:mm:ss') ===" | Tee-Object -FilePath $LOG

Set-Location $ROOT

# 0. Pull latest share counts / manual values from Google Sheet
"[0/3] sync_sheet" | Tee-Object -FilePath $LOG -Append
python sync_sheet.py 2>&1 | Tee-Object -FilePath $LOG -Append

# 1. Fetch latest prices
"[1/3] au-update" | Tee-Object -FilePath $LOG -Append
python -m asset_universe.update 2>&1 | Tee-Object -FilePath $LOG -Append

# 2. Compute TPV + FI@50
"[2/3] fi_tracker" | Tee-Object -FilePath $LOG -Append
python fi_tracker.py 2>&1 | Tee-Object -FilePath $LOG -Append

"=== done $(Get-Date -Format 'HH:mm:ss') ===" | Tee-Object -FilePath $LOG -Append
