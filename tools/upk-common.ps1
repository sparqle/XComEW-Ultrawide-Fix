# Shared helpers for the UPK command scripts. Dot-source this file.

function Find-Tool([string]$Name) {
    $local = Join-Path $PSScriptRoot $Name
    if (Test-Path -LiteralPath $local -PathType Leaf) {
        return $local
    }
    $thirdParty = Join-Path $PSScriptRoot "../third-party/$Name"
    if (Test-Path -LiteralPath $thirdParty -PathType Leaf) {
        return $thirdParty
    }
    $command = Get-Command $Name -CommandType Application -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if (-not $command) {
        throw "Put $Name beside this script, in ../third-party relative to this script, or on PATH."
    }
    return $command.Source
}

function Invoke-Tool([string]$Exe, [string[]]$Paths, [string]$WorkDir) {
    # ProcessStartInfo.ArgumentList is unavailable in Windows PowerShell 5.1.
    # Escape embedded quotes and trailing backslashes for a Windows command line.
    $quotedPaths = @($Paths | ForEach-Object {
        $argument = [regex]::Replace($_, '(\\*)"', '$1$1\"')
        $argument = [regex]::Replace($argument, '(\\+)$', '$1$1')
        '"' + $argument + '"'
    })
    $process = New-Object System.Diagnostics.Process
    try {
        $process.StartInfo.FileName = $Exe
        $process.StartInfo.Arguments = $quotedPaths -join ' '
        $process.StartInfo.WorkingDirectory = $WorkDir
        $process.StartInfo.UseShellExecute = $false
        $process.StartInfo.CreateNoWindow = $true
        $process.StartInfo.RedirectStandardOutput = $true
        $process.StartInfo.RedirectStandardError = $true
        $null = $process.Start()

        # Drain both pipes concurrently so either stream can exceed its buffer.
        $stdout = $process.StandardOutput.ReadToEndAsync()
        $stderr = $process.StandardError.ReadToEndAsync()
        $process.WaitForExit()
        [pscustomobject]@{
            ExitCode = $process.ExitCode
            Output = $stdout.GetAwaiter().GetResult()
            ErrorOutput = $stderr.GetAwaiter().GetResult()
        }
    } finally {
        $process.Dispose()
    }
}

# Return a decompressed copy when available, otherwise use the original package.
# The caller owns WorkDir and removes it after the consuming tool finishes.
function Get-UpkToolInput([string]$DecompressExe, [System.IO.FileInfo]$Package, [string]$WorkDir) {
    $unpacked = Join-Path $WorkDir $Package.Name
    $result = Invoke-Tool $DecompressExe @($Package.FullName, $unpacked) $WorkDir
    if ($result.ExitCode -ne 0 -or
        -not [string]::IsNullOrWhiteSpace($result.ErrorOutput) -or
        $result.Output -match '\berror\b' -or
        -not (Test-Path -LiteralPath $unpacked -PathType Leaf)) {
        # Already-decompressed packages can be read directly.
        return $Package.FullName
    }
    return $unpacked
}
