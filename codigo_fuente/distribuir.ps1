# Crea el ZIP de distribución sin incluir el entorno de desarrollo.
param(
    [string]$Ejecutable = (Join-Path $PSScriptRoot 'dist\LingoLens.exe'),
    [string]$Salida = (Join-Path (Split-Path -Parent $PSScriptRoot) 'LingoLens-GitHub.zip')
)

$ErrorActionPreference = 'Stop'
$raiz = Split-Path -Parent $PSScriptRoot
$temporal = Join-Path ([System.IO.Path]::GetTempPath()) "LingoLens-distribucion-$PID"
$temporalAbsoluto = [System.IO.Path]::GetFullPath($temporal)
$tempRaiz = [System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath())

if (-not $temporalAbsoluto.StartsWith($tempRaiz, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw 'La carpeta temporal calculada no es segura.'
}
if (-not (Test-Path -LiteralPath $Ejecutable)) {
    throw "No existe el ejecutable: $Ejecutable"
}

$excluir = '(^|\\)(\.venv|build|dist|__pycache__|tesseract)(\\|$)|\.py[cod]$'
New-Item -ItemType Directory -Force -Path $temporal | Out-Null
try {
    Copy-Item -LiteralPath $Ejecutable -Destination (Join-Path $temporal 'LingoLens.exe') -Force
    Copy-Item -LiteralPath (Join-Path $raiz 'README.md') -Destination $temporal -Force
    Copy-Item -LiteralPath (Join-Path $raiz '.gitignore') -Destination $temporal -Force

    $archivos = Get-ChildItem -LiteralPath $raiz -File -Recurse |
        Where-Object {
            $relativo = $_.FullName.Substring($raiz.Length + 1)
            $relativo -notmatch $excluir -and
            $_.FullName -notlike "$temporalAbsoluto\*"
        }
    foreach ($archivo in $archivos) {
        $relativo = $archivo.FullName.Substring($raiz.Length + 1)
        $destino = Join-Path $temporal $relativo
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $destino) | Out-Null
        Copy-Item -LiteralPath $archivo.FullName -Destination $destino -Force
    }

    Add-Type -AssemblyName System.IO.Compression
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $salidaAbsoluta = [System.IO.Path]::GetFullPath($Salida)
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $salidaAbsoluta) | Out-Null
    $ordenados = @(
        Get-Item -LiteralPath (Join-Path $temporal 'LingoLens.exe')
        Get-Item -LiteralPath (Join-Path $temporal 'README.md')
        Get-Item -LiteralPath (Join-Path $temporal '.gitignore')
        Get-ChildItem -LiteralPath (Join-Path $temporal 'codigo_fuente') -File -Recurse | Sort-Object FullName
        Get-ChildItem -LiteralPath (Join-Path $temporal 'tests') -File -Recurse | Sort-Object FullName
    )
    $flujo = [System.IO.File]::Open(
        $salidaAbsoluta,
        [System.IO.FileMode]::Create,
        [System.IO.FileAccess]::Write,
        [System.IO.FileShare]::None
    )
    $archivoZip = [System.IO.Compression.ZipArchive]::new(
        $flujo,
        [System.IO.Compression.ZipArchiveMode]::Create,
        $false
    )
    try {
        foreach ($archivo in $ordenados) {
            $nombre = $archivo.FullName.Substring($temporalAbsoluto.Length + 1).Replace('\', '/')
            $entradaZip = $archivoZip.CreateEntry(
                $nombre,
                [System.IO.Compression.CompressionLevel]::Optimal
            )
            $entrada = [System.IO.File]::OpenRead($archivo.FullName)
            $salidaEntrada = $entradaZip.Open()
            try {
                $entrada.CopyTo($salidaEntrada)
            } finally {
                $salidaEntrada.Dispose()
                $entrada.Dispose()
            }
        }
    } finally {
        $archivoZip.Dispose()
        $flujo.Dispose()
    }

    if (-not (Test-Path -LiteralPath $Salida)) {
        throw 'No se generó el ZIP de distribución.'
    }
    $archivoSalida = Get-Item -LiteralPath $Salida
    "ZIP listo: $($archivoSalida.FullName)"
    "Tamaño: $($archivoSalida.Length) bytes"
    "SHA-256: $((Get-FileHash -LiteralPath $Salida -Algorithm SHA256).Hash)"
} finally {
    if (Test-Path -LiteralPath $temporalAbsoluto) {
        Remove-Item -LiteralPath $temporalAbsoluto -Recurse -Force
    }
}
