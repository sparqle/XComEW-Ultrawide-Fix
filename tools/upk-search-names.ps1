# Requires Windows PowerShell 5.1 or PowerShell 7 on Windows.
# Usage: .\upk-search-names.ps1 'C:\Packages' 'soldier|hangar' -IgnoreCase
#        .\upk-search-names.ps1 'C:\Packages\XComGame.upk' 'soldier|hangar' -IgnoreCase
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [Alias('Directory')]
    [string]$Path,

    [Parameter(Mandatory = $true, Position = 1)]
    [string]$Pattern,

    [Alias('i')]
    [switch]$IgnoreCase
)

$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot 'upk-common.ps1')

try {
    if (-not (Test-Path -LiteralPath $Path)) {
        throw "Not a file or directory: $Path"
    }
    $options = [System.Text.RegularExpressions.RegexOptions]::None
    if ($IgnoreCase) {
        $options = [System.Text.RegularExpressions.RegexOptions]::IgnoreCase
    }
    $regex = [regex]::new($Pattern, $options)
    $inputItem = Get-Item -LiteralPath $Path
    if ($inputItem.PSIsContainer) {
        $packages = @(Get-ChildItem -LiteralPath $Path -File |
            Where-Object { $_.Extension -ieq '.upk' } | Sort-Object Name)
    } elseif ($inputItem.Extension -ieq '.upk') {
        $packages = @($inputItem)
    } else {
        throw "Not a .upk file: $Path"
    }
} catch {
    [Console]::Error.WriteLine($_.Exception.Message)
    exit 2
}

if ($packages.Count -eq 0) {
    [Console]::Error.WriteLine('No .upk files found.')
    exit 1
}

$decompress = Find-Tool 'DecompressLZO.exe'
$extract = Find-Tool 'ExtractNameLists.exe'

$matched = $false
$failed = $false
foreach ($package in $packages) {
    $temp = $null
    try {
        $temp = Join-Path ([System.IO.Path]::GetTempPath()) ('upk_names_' + [guid]::NewGuid())
        $null = New-Item -ItemType Directory -Path $temp
        $extractInput = Get-UpkToolInput $decompress $package $temp
        $result = Invoke-Tool $extract @($extractInput) $temp
        if ($result.ExitCode -ne 0) {
            throw "ExtractNameLists exited with code $($result.ExitCode).`n$($result.Output)$($result.ErrorOutput)"
        }

        # Find regexp
        $number = 0
        foreach ($line in ($result.Output -split '\r\n|\n|\r')) {
            $number++
            if ($regex.IsMatch($line)) {
                Write-Output ('{0}:{1}:{2}' -f $package.Name, $number, $line)
                $matched = $true
            }
        }
        if ($result.ErrorOutput) {
            [Console]::Error.Write($result.ErrorOutput)
        }
    } catch {
        $failed = $true
        [Console]::Error.WriteLine(('ERROR: {0}: {1}' -f $package.Name, $_.Exception.Message))
    } finally {
        if ($temp -and (Test-Path -LiteralPath $temp)) {
            Remove-Item -LiteralPath $temp -Recurse -Force
        }
    }
}

# grep-style exit codes: 0 = matches, 1 = none, 2 = processing error.
if ($failed) { exit 2 }
if ($matched) { exit 0 }
exit 1
