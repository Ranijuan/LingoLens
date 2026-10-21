# Construye un único .exe con Python, Qt, OCR y el núcleo C.
$ErrorActionPreference = 'Stop'
$raiz = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $raiz '.venv\Scripts\python.exe'
$tesseractOrigen = 'C:\Program Files\Tesseract-OCR'
$tesseractDestino = Join-Path $raiz 'recursos\tesseract'

if (-not (Test-Path -LiteralPath $python)) {
    throw 'No existe .venv. Sigue los pasos de documentacion\INSTALACION.md.'
}
if (-not (Test-Path -LiteralPath (Join-Path $tesseractOrigen 'tesseract.exe'))) {
    throw 'No encuentro Tesseract en C:\Program Files\Tesseract-OCR.'
}

& (Join-Path $raiz 'construir.ps1')
New-Item -ItemType Directory -Force -Path `
    (Join-Path $tesseractDestino 'tessdata') | Out-Null
Copy-Item -LiteralPath (Join-Path $tesseractOrigen 'tesseract.exe') `
    -Destination $tesseractDestino -Force
Get-ChildItem -LiteralPath $tesseractOrigen -Filter '*.dll' -File |
    ForEach-Object {
        Copy-Item -LiteralPath $_.FullName -Destination $tesseractDestino -Force
    }
Copy-Item -LiteralPath (Join-Path $tesseractOrigen 'tessdata\eng.traineddata') `
    -Destination (Join-Path $tesseractDestino 'tessdata') -Force

$modeloEspanol = Join-Path $tesseractOrigen 'tessdata\spa.traineddata'
$destinoEspanol = Join-Path $tesseractDestino 'tessdata\spa.traineddata'
if (Test-Path -LiteralPath $modeloEspanol) {
    Copy-Item -LiteralPath $modeloEspanol -Destination $destinoEspanol -Force
} elseif (-not (Test-Path -LiteralPath $destinoEspanol)) {
    $url = 'https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/main/spa.traineddata'
    Invoke-WebRequest -Uri $url -OutFile $destinoEspanol
}

$dllNucleo = Join-Path $raiz 'nucleo\bin\nucleo.dll'
if (-not (Test-Path -LiteralPath $destinoEspanol)) {
    throw 'Falta el modelo de OCR en español spa.traineddata.'
}
$archivoTesseract = Join-Path $raiz 'recursos\tesseract.zip'
Compress-Archive -Path (Join-Path $tesseractDestino '*') `
    -DestinationPath $archivoTesseract -CompressionLevel Optimal -Force

$salida = Join-Path $raiz 'dist'
$trabajo = Join-Path $raiz 'build'
$argumentos = @(
    '-m', 'PyInstaller',
    '--noconfirm', '--clean',
    (Join-Path $raiz 'LingoLens.spec')
)
Push-Location $raiz
try {
    & $python @argumentos
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller terminó con código $LASTEXITCODE."
    }
} finally {
    Pop-Location
}

$ejecutable = Join-Path $salida 'LingoLens.exe'
if (-not (Test-Path -LiteralPath $ejecutable)) {
    throw 'PyInstaller no generó dist\LingoLens.exe.'
}
"Ejecutable único listo: $ejecutable"
"Tamaño: $([math]::Round((Get-Item -LiteralPath $ejecutable).Length / 1MB, 1)) MB"
