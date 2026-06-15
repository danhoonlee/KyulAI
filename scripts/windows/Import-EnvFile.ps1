param(
    [string]$Path = ".env.local"
)

if (-not (Test-Path $Path)) {
    return
}

foreach ($rawLine in Get-Content $Path) {
    $line = $rawLine.Trim()
    if (-not $line -or $line.StartsWith("#")) {
        continue
    }
    $parts = $line.Split("=", 2)
    if ($parts.Count -ne 2) {
        continue
    }
    $name = $parts[0].Trim()
    $value = $parts[1].Trim().Trim('"').Trim("'")
    if ($name) {
        Set-Item -Path "Env:$name" -Value $value
    }
}
