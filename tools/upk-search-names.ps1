# Requires Windows PowerShell 5.1 or PowerShell 7 on Windows.
# Usage: .\search-upk-names.ps1 'C:\Packages' 'soldier|hangar' -IgnoreCase
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$Directory,

    [Parameter(Mandatory = $true, Position = 1)]
    [string]$Pattern,

    [Alias('i')]
    [switch]$IgnoreCase
)

$ErrorActionPreference = 'Stop'

function Find-Tool([string]$Name) {
    $local = Join-Path $PSScriptRoot $Name
    if (Test-Path -LiteralPath $local -PathType Leaf) {
        return $local
    }
    $command = Get-Command $Name -CommandType Application -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if (-not $command) {
        throw "Put $Name beside this script or on PATH."
    }
    return $command.Source
}

function Invoke-Tool([string]$Exe, [string[]]$Paths, [string]$WorkDir) {
    # Windows file paths cannot contain double quotes. Quote every argument
    # because Start-Process joins ArgumentList into a single command line.
    $quotedPaths = @($Paths | ForEach-Object { '"' + $_ + '"' })
    $stdout = Join-Path $WorkDir 'stdout.txt'
    $stderr = Join-Path $WorkDir 'stderr.txt'
    $process = Start-Process -FilePath $Exe -ArgumentList $quotedPaths `
        -WorkingDirectory $WorkDir -NoNewWindow -Wait -PassThru `
        -RedirectStandardOutput $stdout -RedirectStandardError $stderr
    [pscustomobject]@{
        ExitCode = $process.ExitCode
        Output = [System.IO.File]::ReadAllText($stdout)
        ErrorOutput = [System.IO.File]::ReadAllText($stderr)
    }
}

try {
    if (-not (Test-Path -LiteralPath $Directory -PathType Container)) {
        throw "Not a directory: $Directory"
    }
    $options = [System.Text.RegularExpressions.RegexOptions]::None
    if ($IgnoreCase) {
        $options = [System.Text.RegularExpressions.RegexOptions]::IgnoreCase
    }
    $regex = [regex]::new($Pattern, $options)
    $decompress = Find-Tool 'DecompressLZO.exe'
    $extract = Find-Tool 'ExtractNameLists.exe'
    $packages = @(Get-ChildItem -LiteralPath $Directory -File |
        Where-Object { $_.Extension -ieq '.upk' } | Sort-Object Name)
} catch {
    [Console]::Error.WriteLine($_.Exception.Message)
    exit 2
}

if ($packages.Count -eq 0) {
    [Console]::Error.WriteLine('No .upk files found.')
    exit 1
}

$matched = $false
$failed = $false
foreach ($package in $packages) {
    $temp = $null
    try {
        $temp = Join-Path ([System.IO.Path]::GetTempPath()) ('upk_names_' + [guid]::NewGuid())
        $null = New-Item -ItemType Directory -Path $temp
        $unpacked = Join-Path $temp $package.Name
        $result = Invoke-Tool $decompress @($package.FullName, $unpacked) $temp
        $extractInput = $unpacked
        if ($result.ExitCode -ne 0 -or
            -not [string]::IsNullOrWhiteSpace($result.ErrorOutput) -or
            $result.Output -match '\berror\b' -or
            -not (Test-Path -LiteralPath $unpacked -PathType Leaf)) {
            # Already-decompressed packages can be read directly.
            $extractInput = $package.FullName
        }
        $result = Invoke-Tool $extract @($extractInput) $temp
        if ($result.ExitCode -ne 0) {
            throw "ExtractNameLists exited with code $($result.ExitCode).`n$($result.Output)$($result.ErrorOutput)"
        }
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
