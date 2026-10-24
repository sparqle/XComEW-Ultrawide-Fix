# Requires Windows PowerShell 5.1 or PowerShell 7 on Windows.
# Usage: .\upk-find-object.ps1 'C:\Packages\Command1.upk' 'gfxStrategyHUD.StrategyHUD'
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$UpkFile,

    [Parameter(Mandatory = $true, Position = 1)]
    [ValidateNotNullOrEmpty()]
    [string]$EntryName
)

$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot 'upk-common.ps1')

$temp = $null
$exitCode = 0
try {
    if (-not (Test-Path -LiteralPath $UpkFile -PathType Leaf)) {
        throw "Not a file: $UpkFile"
    }
    $package = Get-Item -LiteralPath $UpkFile
    $decompress = Find-Tool 'DecompressLZO.exe'
    $find = Find-Tool 'FindObjectEntry.exe'

    $temp = Join-Path ([System.IO.Path]::GetTempPath()) ('upk_find_object_' + [guid]::NewGuid())
    $null = New-Item -ItemType Directory -Path $temp
    $findInput = Get-UpkToolInput $decompress $package $temp
    $result = Invoke-Tool $find @($findInput, $EntryName) $temp
    if ($result.ExitCode -ne 0) {
        throw "FindObjectEntry exited with code $($result.ExitCode).`n$($result.Output)$($result.ErrorOutput)"
    }
    [Console]::Out.Write($result.Output)
    if ($result.ErrorOutput) {
        [Console]::Error.Write($result.ErrorOutput)
    }
} catch {
    [Console]::Error.WriteLine($_.Exception.Message)
    $exitCode = 2
} finally {
    if ($temp -and (Test-Path -LiteralPath $temp)) {
        Remove-Item -LiteralPath $temp -Recurse -Force
    }
}
exit $exitCode
