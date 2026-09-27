# Original geometric artwork; regenerate with PowerShell on Windows.
Add-Type -AssemblyName System.Drawing
$assetDirectory = Join-Path $PSScriptRoot '../assets'
New-Item -ItemType Directory -Force -Path $assetDirectory | Out-Null
$master = New-Object System.Drawing.Bitmap 1024, 1024
$graphics = [System.Drawing.Graphics]::FromImage($master)
$graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
$graphics.ScaleTransform(4, 4)
$dark = New-Object System.Drawing.SolidBrush ([System.Drawing.ColorTranslator]::FromHtml('#142B3D'))
$cyan = New-Object System.Drawing.SolidBrush ([System.Drawing.ColorTranslator]::FromHtml('#43D9E6'))
$white = New-Object System.Drawing.SolidBrush ([System.Drawing.ColorTranslator]::FromHtml('#F0FDFF'))
function Fill-Shape($brush, $coordinates) {
    $points = for ($i = 0; $i -lt $coordinates.Count; $i += 2) {
        New-Object System.Drawing.PointF $coordinates[$i], $coordinates[$i + 1]
    }
    $graphics.FillPolygon($brush, [System.Drawing.PointF[]]$points)
}
# Broad screen, short pedestal, and a heavy outline that survives small sizes.
$graphics.FillRectangle($dark, 116, 160, 24, 34)
Fill-Shape $dark @(92, 190, 164, 190, 176, 204, 80, 204)
Fill-Shape $dark @(20, 48, 236, 48, 248, 60, 248, 152, 236, 164, 20, 164, 8, 152, 8, 60)
Fill-Shape $cyan @(24, 60, 232, 60, 236, 64, 236, 144, 232, 148, 24, 148, 20, 144, 20, 64)
Fill-Shape $dark @(28, 68, 228, 68, 228, 140, 28, 140)
Fill-Shape $white @(40, 104, 64, 84, 64, 97, 112, 97, 112, 111, 64, 111, 64, 124)
Fill-Shape $white @(216, 104, 192, 84, 192, 97, 144, 97, 144, 111, 192, 111, 192, 124)
$graphics.Dispose()
$dark.Dispose()
$cyan.Dispose()
$white.Dispose()
$sizes = @(16, 20, 24, 32, 48, 64, 128, 256)
$images = @()
foreach ($size in $sizes) {
    $bitmap = New-Object System.Drawing.Bitmap $size, $size
    $canvas = [System.Drawing.Graphics]::FromImage($bitmap)
    $canvas.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
    $canvas.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
    $canvas.DrawImage($master, 0, 0, $size, $size)
    $stream = New-Object System.IO.MemoryStream
    $bitmap.Save($stream, [System.Drawing.Imaging.ImageFormat]::Png)
    $images += ,$stream.ToArray()
    if ($size -eq 256) {
        $bitmap.Save((Join-Path $assetDirectory 'ultrawide.png'), [System.Drawing.Imaging.ImageFormat]::Png)
    }
    $stream.Dispose()
    $canvas.Dispose()
    $bitmap.Dispose()
}
$master.Dispose()
$file = [System.IO.File]::Create((Join-Path $assetDirectory 'ultrawide.ico'))
$writer = New-Object System.IO.BinaryWriter $file
try {
    $writer.Write([uint16]0)
    $writer.Write([uint16]1)
    $writer.Write([uint16]$sizes.Count)
    $offset = 6 + 16 * $sizes.Count
    for ($i = 0; $i -lt $sizes.Count; $i++) {
        $dimension = if ($sizes[$i] -eq 256) { 0 } else { $sizes[$i] }
        $writer.Write([byte]$dimension)
        $writer.Write([byte]$dimension)
        $writer.Write([byte]0)
        $writer.Write([byte]0)
        $writer.Write([uint16]1)
        $writer.Write([uint16]32)
        $writer.Write([uint32]$images[$i].Length)
        $writer.Write([uint32]$offset)
        $offset += $images[$i].Length
    }
    foreach ($bytes in $images) { $writer.Write([byte[]]$bytes) }
} finally {
    $writer.Dispose()
}
