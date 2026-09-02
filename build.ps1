#requires -version 5
<#
Rebuilds the Traditional Chinese language pack from the upstream Simplified
Chinese release. Everything under out\ and work\ (except work\pack102) is
regenerated, so it is safe to delete them and run this again.

Prerequisite: the upstream v1.0.2 language pack extracted to work\pack102\ so
that work\pack102\release\content\ exists. Get it from
https://github.com/wmltogether/ZLD-TWW-HD-Chinese-Localization-Project/releases
#>
param(
    [string]$Upstream = "work\pack102\release",
    [string]$Ttf = "C:\Windows\Fonts\NotoSansTC-VF.ttf"
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$py = ".\.venv\Scripts\python.exe"

$srcPack = "$Upstream\content\Common\Pack\permanent_2d_UsEnglish.pack"
$srcTitle = "$Upstream\content\Common\Layout\Title_00.szs"
foreach ($f in $py, $srcPack, $srcTitle) {
    if (-not (Test-Path $f)) { throw "missing $f - see the header of this script" }
}

$outPack = "out\release\content\Common\Pack\permanent_2d_UsEnglish.pack"
$outTitle = "out\release\content\Common\Layout\Title_00.szs"
$origFonts = "work\tree\permanent_2d_UsEnglish"
New-Item -ItemType Directory -Force out, work\out_font, work\out_title,
    (Split-Path $outPack), (Split-Path $outTitle) | Out-Null

function Step($n, $msg) { Write-Host "`n=== [$n] $msg" -ForegroundColor Cyan }

Step 1 "unpack the language pack"
& $py tools\expand_tree.py $srcPack work\tree out\inventory.txt

Step 2 "convert every MSBT to Traditional Chinese (OpenCC s2twp)"
& $py tools\convert_text.py work\tree work\tree_zhtw out\convert_report.json s2twp

Step 2.5 "apply the hand-reviewed per-message corrections"
& $py tools\apply_overrides.py work\tree_zhtw text\overrides.json
if ($LASTEXITCODE -ne 0) { throw "text\overrides.json has entries that no longer apply" }

Step 3 "work out which glyphs the menu fonts need"
& $py tools\menu_chars.py "$origFonts\CKingMain_bffnt.szs\CKingMain.bffnt" `
    work\tree work\tree_zhtw out\menu_chars.txt

Step 4 "add glyphs to the three fonts that carry Chinese text"
& $py tools\build_font.py "$origFonts\CKingMsg_bffnt.szs\CKingMsg.bffnt" `
    work\out_font\CKingMsg.bffnt --text-root work\tree_zhtw --ttf $Ttf `
    --report out\font_build_msg.json
foreach ($f in "CKingMain", "CKingMainL") {
    & $py tools\build_font.py "$origFonts\${f}_bffnt.szs\$f.bffnt" `
        "work\out_font\$f.bffnt" --chars-file out\menu_chars.txt --ttf $Ttf `
        --report "out\font_build_$f.json"
}

Step 5 "install the hand-made title logo artwork"
& $py tools\dump_bflim.py $srcTitle out\title
New-Item -ItemType Directory -Force out\title\new | Out-Null
Copy-Item art\texture\*.png out\title\new\ -Force
Get-ChildItem out\title\new | ForEach-Object { "  $($_.Name)" }

Step 6 "repack"
& $py tools\repack.py $srcPack $outPack --msbt-root work\tree_zhtw --font-dir work\out_font
& $py tools\pack_bflim.py $srcTitle $outTitle --png-dir out\title\new

Step 7 "verify the rebuilt pack"
& $py tools\verify_release.py $outPack out\verify_release.txt
& $py tools\menu_chars.py work\out_font\CKingMain.bffnt `
    work\tree work\tree_zhtw out\menu_chars_after.txt
if ((Get-Item out\menu_chars_after.txt).Length -ne 0) {
    Write-Warning "menu fonts are still missing glyphs - see out\menu_chars_after.txt"
}

Step 8 "package"
Copy-Item release-README.txt out\release\README.txt -Force
$zip = "out\ZLD-TWW-HD-zhTW-v1.0.2-tw1.zip"
Remove-Item $zip -ErrorAction SilentlyContinue
Compress-Archive -Path out\release\* -DestinationPath $zip -CompressionLevel Optimal

Step 9 "build the Cemu graphic pack (overrides files without unpacking the disc image)"
$gp = "out\cemu\TWWHD_zhTW"
Remove-Item -Recurse -Force $gp -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force $gp | Out-Null
Copy-Item cemu-rules.txt "$gp\rules.txt"
Copy-Item release-README.txt "$gp\README.txt"
Copy-Item -Recurse out\release\content "$gp\content"
$gpZip = "out\TWWHD_zhTW_CemuGraphicPack.zip"
Remove-Item $gpZip -ErrorAction SilentlyContinue
Compress-Archive -Path $gp -DestinationPath $gpZip -CompressionLevel Optimal

Write-Host "`nDone" -ForegroundColor Green
Write-Host "  loose files : $zip"
Write-Host "  Cemu pack   : $gpZip"
