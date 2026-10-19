# Run from any directory: powershell -File tools/build.ps1
# Each mods/<name>/mod.json supplies a version and an ordered files array.
[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
# IDE output consoles do not reliably render Compress-Archive's progress display.
$ProgressPreference = 'SilentlyContinue'

$projectDirectory = Split-Path -Parent $PSScriptRoot
$modsDirectory = Join-Path $projectDirectory 'mods'
$distDirectory = Join-Path $projectDirectory 'dist'
$utf8 = [System.Text.UTF8Encoding]::new($false)

New-Item -ItemType Directory -Force -Path $distDirectory | Out-Null

foreach ($modDirectory in Get-ChildItem -LiteralPath $modsDirectory -Directory | Sort-Object Name) {
    $manifestPath = Join-Path $modDirectory.FullName 'mod.json'
    if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) {
        continue
    }

    $manifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if (-not $manifest.PSObject.Properties['version'] -or
        $manifest.version -isnot [string] -or
        $manifest.version -notmatch '^[A-Za-z0-9][A-Za-z0-9._-]*$') {
        throw "Invalid or missing version in $manifestPath"
    }
    if (-not $manifest.PSObject.Properties['files'] -or
        $manifest.files -isnot [array] -or $manifest.files.Count -eq 0) {
        throw "Expected a nonempty files array in $manifestPath"
    }

    $parts = foreach ($file in $manifest.files) {
        if ($file -isnot [string] -or [string]::IsNullOrWhiteSpace($file) -or
            [System.IO.Path]::GetExtension($file) -ine '.txt') {
            throw "Expected a .txt file name in $manifestPath"
        }
        $sourcePath = [System.IO.Path]::GetFullPath((Join-Path $modDirectory.FullName $file))
        $sourceRoot = $modsDirectory + [System.IO.Path]::DirectorySeparatorChar
        if (-not $sourcePath.StartsWith($sourceRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "Source file must be inside ${modsDirectory}: $file"
        }
        [System.IO.File]::ReadAllText($sourcePath, $utf8).Trim([char[]]"`r`n")
    }

    $outputPath = Join-Path $modDirectory.FullName ($modDirectory.Name + '.txt')
    # Insert two blank line between trimmed fragments.
    [System.IO.File]::WriteAllText($outputPath, ($parts -join "`r`n`r`n`r`n"), $utf8)

    $archivePath = Join-Path $distDirectory ("{0}-{1}.zip" -f $modDirectory.Name, $manifest.version)
    Compress-Archive -LiteralPath $outputPath -DestinationPath $archivePath -Force
    Write-Host "Built $outputPath"
    Write-Host "Created $archivePath"
}
