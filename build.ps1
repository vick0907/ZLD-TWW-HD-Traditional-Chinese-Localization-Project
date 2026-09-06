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
    [string]$Ttf = "C:\Windows\Fonts\NotoSansTC-VF.ttf",
    # Bump this for every release; it names both zips and must match the git tag.
    [string]$Version = "tw-v1.0.10"
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

Step 2.5 "apply all hand-reviewed correction passes"
& $py tools\apply_overrides.py work\tree_zhtw text\overrides.json
if ($LASTEXITCODE -ne 0) { throw "text\overrides.json has entries that no longer apply" }
& $py tools\apply_overrides.py work\tree_zhtw text\review_pass2.json
if ($LASTEXITCODE -ne 0) { throw "text\review_pass2.json has entries that no longer apply" }
& $py tools\apply_overrides.py work\tree_zhtw text\readability_pass.json
if ($LASTEXITCODE -ne 0) { throw "text\readability_pass.json has entries that no longer apply" }
& $py tools\apply_overrides.py work\tree_zhtw text\semantic_pass.json
if ($LASTEXITCODE -ne 0) { throw "text\semantic_pass.json has entries that no longer apply" }

Step 2.6 "rebuild the bilingual alignment and run localization QA"
& $py tools\test_qa_actions.py
if ($LASTEXITCODE -ne 0) { throw "action QA regression tests failed" }
& $py tools\align_en.py work\tree_en work\tree_zhtw `
    --tsv out\bilingual.tsv --flagged out\review_flagged.txt --glossary out\glossary.txt
if ($LASTEXITCODE -ne 0) { throw "English/Chinese alignment failed" }
& $py tools\qa_align.py out\bilingual.tsv out\qa_report.txt
if ($LASTEXITCODE -ne 0) { throw "localization QA failed" }
& $py tools\audit_register.py out\bilingual.tsv out\register_audit.txt
if ($LASTEXITCODE -ne 0) { throw "register audit failed" }
# Advisory: most hits are fragments that legitimately recur, so a human reads it.
& $py tools\audit_overrides.py out\bilingual.tsv `
    text\overrides.json text\review_pass2.json text\readability_pass.json `
    text\semantic_pass.json `
    out\override_audit.txt

Step 3 "work out which glyphs the menu fonts need"
& $py tools\menu_chars.py "$origFonts\CKingMain_bffnt.szs\CKingMain.bffnt" `
    work\tree work\tree_zhtw out\menu_chars.txt

Step 4 "reproduce the tested base fonts, then append new glyphs"
& $py tools\build_font.py "$origFonts\CKingMsg_bffnt.szs\CKingMsg.bffnt" `
    work\out_font\CKingMsg_base.bffnt --ttf $Ttf `
    --chars-file text\CKingMsg_base_v109.txt --report out\font_build_msg_base.json
if ($LASTEXITCODE -ne 0) { throw "dialogue base font build failed" }
& $py tools\redraw_han_font.py work\out_font\CKingMsg_base.bffnt `
    work\out_font\CKingMsg_base500.bffnt --chars-file text\CKingMsg_base_v109.txt `
    --ttf $Ttf --variation 500 --report out\font_redraw_msg.json
if ($LASTEXITCODE -ne 0) { throw "weight-500 dialogue font redraw failed" }
if ((Get-FileHash work\out_font\CKingMsg_base500.bffnt -Algorithm SHA256).Hash -ne `
    "db1d07073c8898a2156a2951024c44243b8bdcfb0bdebbad4af02b6d1936e051") {
    throw "dialogue base font differs from tested tw-v1.0.9"
}
& $py tools\build_font.py work\out_font\CKingMsg_base500.bffnt `
    work\out_font\CKingMsg.bffnt --text-root work\tree_zhtw --ttf $Ttf `
    --variation 500 --chars-file text\CKingMsg_legacy_chars.txt --report out\font_build_msg.json
if ($LASTEXITCODE -ne 0) { throw "dialogue glyph append failed" }
Remove-Item work\out_font\CKingMsg_base.bffnt, work\out_font\CKingMsg_base500.bffnt
foreach ($f in "CKingMain", "CKingMainL") {
    & $py tools\build_font.py "$origFonts\${f}_bffnt.szs\$f.bffnt" `
        "work\out_font\${f}_base.bffnt" --chars-file text\CKingMain_base_v109.txt --ttf $Ttf `
        --report "out\font_build_${f}_base.json"
    if ($LASTEXITCODE -ne 0) { throw "$f base font build failed" }
    if ((Get-FileHash "work\out_font\${f}_base.bffnt" -Algorithm SHA256).Hash -ne `
        "8b68bd1a702ed71bb806d2a159b8326a443ecdda0f588b62b68855faead02bed") {
        throw "$f base font differs from tested tw-v1.0.9"
    }
    & $py tools\build_font.py "work\out_font\${f}_base.bffnt" `
        "work\out_font\$f.bffnt" --chars-file out\menu_chars.txt --ttf $Ttf `
        --report "out\font_build_$f.json"
    if ($LASTEXITCODE -ne 0) { throw "$f glyph append failed" }
    Remove-Item "work\out_font\${f}_base.bffnt"
}

Step 5 "install the hand-made title logo artwork"
& $py tools\dump_bflim.py $srcTitle out\title
New-Item -ItemType Directory -Force out\title\new | Out-Null
Copy-Item art\texture\*.png out\title\new\ -Force
Get-ChildItem out\title\new | ForEach-Object { "  $($_.Name)" }

Step 6 "repack"
& $py tools\repack.py $srcPack $outPack --msbt-root work\tree_zhtw --font-dir work\out_font
& $py tools\build_title.py $srcTitle $outTitle `
    --logo out\title\new\TitleLogoZelda_00_l.png `
    --ruby out\title\new\TitleLogoZeldaRuby_00_l.png `
    --subtitle out\title\new\TitleLogoWindwakerJ_00_l.png
if ($LASTEXITCODE -ne 0) { throw "title logo build or verification failed" }

Step 7 "verify the rebuilt pack"
& $py tools\verify_release.py $outPack out\verify_release.txt
& $py tools\menu_chars.py work\out_font\CKingMain.bffnt `
    work\tree work\tree_zhtw out\menu_chars_after.txt
if ((Get-Item out\menu_chars_after.txt).Length -ne 0) {
    Write-Warning "menu fonts are still missing glyphs - see out\menu_chars_after.txt"
}

Step 8 "package"
if ((Get-Content release-README.txt -Raw) -notmatch [regex]::Escape("ZLD-TWW-HD-zhTW-$Version.zip")) {
    throw "release-README.txt still names an older zip - update its download section for $Version"
}
Copy-Item release-README.txt out\release\README.txt -Force
$zip = "out\ZLD-TWW-HD-zhTW-$Version.zip"
Remove-Item $zip -ErrorAction SilentlyContinue
Compress-Archive -Path out\release\* -DestinationPath $zip -CompressionLevel Optimal

Step 9 "build the Cemu graphic pack (overrides files without unpacking the disc image)"
$gp = "out\cemu\TWWHD_zhTW"
Remove-Item -Recurse -Force $gp -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force $gp | Out-Null
Copy-Item cemu-rules.txt "$gp\rules.txt"
Copy-Item release-README.txt "$gp\README.txt"
Copy-Item -Recurse out\release\content "$gp\content"
$gpZip = "out\TWWHD_zhTW_CemuGraphicPack-$Version.zip"
Remove-Item $gpZip -ErrorAction SilentlyContinue
Compress-Archive -Path $gp -DestinationPath $gpZip -CompressionLevel Optimal

Write-Host "`nDone" -ForegroundColor Green
Write-Host "  loose files : $zip"
Write-Host "  Cemu pack   : $gpZip"
