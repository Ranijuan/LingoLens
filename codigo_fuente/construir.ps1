# Compila el núcleo en C. Los avisos se tratan como errores para detectarlos pronto.
$ErrorActionPreference = 'Stop'
$raiz = Split-Path -Parent $MyInvocation.MyCommand.Path
$salida = Join-Path $raiz 'nucleo\bin'
New-Item -ItemType Directory -Force -Path $salida | Out-Null

$gcc = Get-Command gcc -ErrorAction SilentlyContinue
if (-not $gcc) {
    throw 'No encuentro GCC. Instala MinGW-w64 y vuelve a ejecutar este archivo.'
}

$dll = Join-Path $salida 'nucleo.dll'
& $gcc.Source -std=c11 -O3 -Wall -Wextra -Werror -shared -static-libgcc `
    (Join-Path $raiz 'nucleo\nucleo.c') `
    -I (Join-Path $raiz 'nucleo') -o $dll
if ($LASTEXITCODE -ne 0) {
    throw "La compilación de C terminó con código $LASTEXITCODE."
}

"Núcleo C compilado: $dll"
"Tamaño: $([math]::Round((Get-Item -LiteralPath $dll).Length / 1KB, 1)) KB"
