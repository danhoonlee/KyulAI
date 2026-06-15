param(
    [switch]$PublicOnly
)

$ErrorActionPreference = "Continue"

$targets = @()
if (-not $PublicOnly) {
    $targets += @(
        @{ Name = "DD local"; Url = "http://127.0.0.1:8000/health" },
        @{ Name = "Injection local"; Url = "http://127.0.0.1:8010/health" }
    )
}
$targets += @(
    @{ Name = "Laminate public"; Url = "https://laminate.luvelox.com/health" },
    @{ Name = "Injection public"; Url = "https://injection.luvelox.com/health" },
    @{ Name = "DD legacy public"; Url = "https://dd.cafedecafe.co.kr/health" },
    @{ Name = "Injection legacy public"; Url = "https://injection.cafedecafe.co.kr/health" }
)

foreach ($target in $targets) {
    try {
        $response = Invoke-WebRequest -Uri $target.Url -UseBasicParsing -TimeoutSec 10
        Write-Host ("{0}: HTTP {1} {2}" -f $target.Name, $response.StatusCode, $response.Content)
    } catch {
        Write-Host ("{0}: FAILED {1}" -f $target.Name, $_.Exception.Message)
    }
}
