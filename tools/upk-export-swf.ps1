# Requires Windows PowerShell 5.1 or PowerShell 7 on Windows.
# Usage: .\upk-export-swf.ps1 'Command1.upk' 'gfxStrategyHUD.StrategyHUD' '.\StrategyHUD.swf'
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$UpkFile,

    [Parameter(Mandatory = $true, Position = 1)]
    [ValidateNotNullOrEmpty()]
    [string]$EntryName,

    [Parameter(Position = 2)]
    [string]$OutputFile,

    [switch]$Force
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'upk-common.ps1')

$temp = $null
$exitCode = 0
try {
    if (-not (Test-Path -LiteralPath $UpkFile -PathType Leaf)) {
        throw "Not a file: $UpkFile"
    }
    if (-not $OutputFile) { $OutputFile = ($EntryName -replace '[^\w.-]', '_') + '.swf' }
    $destination = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($OutputFile)
    $package = Get-Item -LiteralPath $UpkFile
    if ([string]::Equals($destination, $package.FullName, [StringComparison]::OrdinalIgnoreCase)) {
        throw 'The output file must not be the input package.'
    }
    $decompress = Find-Tool 'DecompressLZO.exe'
    $find = Find-Tool 'FindObjectEntry.exe'
    $temp = Join-Path ([IO.Path]::GetTempPath()) ('upk_export_swf_' + [guid]::NewGuid())
    $null = New-Item -ItemType Directory -Path $temp
    $inputFile = Get-UpkToolInput $decompress $package $temp
    $result = Invoke-Tool $find @($inputFile, $EntryName) $temp
    if ($result.ExitCode -ne 0) {
        throw "FindObjectEntry exited with code $($result.ExitCode).`n$($result.Output)$($result.ErrorOutput)"
    }
    if ($result.Output -notmatch "Found Export Object:[\s\S]*?SwfMovie'") {
        throw "Not an exported SwfMovie: $EntryName"
    }
    $sizeMatch = [regex]::Match($result.Output, 'SerialSize:\s*0x([0-9A-Fa-f]+)')
    $offsetMatch = [regex]::Match($result.Output, 'SerialOffset:\s*0x([0-9A-Fa-f]+)')
    if (-not $sizeMatch.Success -or -not $offsetMatch.Success) {
        throw 'Could not read the object byte range from FindObjectEntry output.'
    }
    $size = [Convert]::ToInt32($sizeMatch.Groups[1].Value, 16)
    $offset = [Convert]::ToInt64($offsetMatch.Groups[1].Value, 16)
    $stream = [IO.File]::OpenRead($inputFile)
    try {
        if ($size -lt 12 -or $offset + $size -gt $stream.Length) { throw 'Invalid object byte range.' }
        $null = $stream.Seek($offset, [IO.SeekOrigin]::Begin)
        $reader = New-Object IO.BinaryReader($stream)
        $data = $reader.ReadBytes($size)
    } finally { $stream.Dispose() }

    # UE3 stores RawData as a byte array: Int32 length followed by the movie.
    # Require a plausible header and array length, rather than copying the rest
    # of the export (which can contain additional native fields).
    $candidates = @()
    for ($i = 4; $i -le $data.Length - 8; $i++) {
        if ($data[$i] -notin 67, 70, 71, 90) { continue }
        $signature = [Text.Encoding]::ASCII.GetString($data, $i, 3)
        if ($signature -notin 'FWS', 'CWS', 'ZWS', 'GFX', 'CFX') { continue }
        $length = [BitConverter]::ToInt32($data, $i - 4)
        $movieLength = [BitConverter]::ToUInt32($data, $i + 4)
        if ($length -lt 8 -or $length -gt $data.Length - $i -or
            $data[$i + 3] -eq 0 -or $movieLength -lt 8) { continue }
        if ($signature -in 'FWS', 'GFX' -and $movieLength -ne $length) { continue }
        $candidates += [pscustomobject]@{ Offset = $i; Length = $length; Signature = $signature }
    }
    if ($candidates.Count -ne 1) {
        throw "Expected one embedded SWF/GFX byte array; found $($candidates.Count)."
    }
    $movie = $candidates[0]
    $bytes = New-Object byte[] $movie.Length
    [Array]::Copy($data, $movie.Offset, $bytes, 0, $movie.Length)
    if ($movie.Signature -eq 'GFX') {
        $bytes[0] = 70; $bytes[1] = 87; $bytes[2] = 83
    } elseif ($movie.Signature -eq 'CFX') {
        $bytes[0] = 67; $bytes[1] = 87; $bytes[2] = 83
    }
    $mode = [IO.FileMode]::CreateNew
    if ($Force) { $mode = [IO.FileMode]::Create }
    $output = [IO.File]::Open($destination, $mode, [IO.FileAccess]::Write, [IO.FileShare]::None)
    try { $output.Write($bytes, 0, $bytes.Length) } finally { $output.Dispose() }
    Write-Output "Exported $EntryName to $destination ($($bytes.Length) bytes; source $($movie.Signature))."
} catch {
    [Console]::Error.WriteLine($_.Exception.Message)
    $exitCode = 2
} finally {
    if ($temp -and (Test-Path -LiteralPath $temp)) {
        Remove-Item -LiteralPath $temp -Recurse -Force
    }
}
exit $exitCode
