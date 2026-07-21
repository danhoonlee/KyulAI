param(
    [switch]$PublicOnly,
    [switch]$LocalOnly,
    [switch]$Ready,
    [switch]$Strict,
    [int]$Retries = 1,
    [int]$RetryDelaySec = 3,
    [string[]]$PublicBaseUrls = @(
        "https://imperialax.com",
        "https://www.imperialax.com",
        "https://ai.imperialax.com",
        "https://app.imperialax.com",
        "https://laminate.imperialax.com",
        "https://dd.imperialax.com",
        "https://injection.imperialax.com",
        "https://cafedecafe.co.kr",
        "https://www.cafedecafe.co.kr",
        "https://laminate.cafedecafe.co.kr",
        "https://dd.cafedecafe.co.kr",
        "https://injection.cafedecafe.co.kr"
    )
)

$ErrorActionPreference = "Continue"
if ($PublicOnly -and $LocalOnly) {
    throw "Choose either -PublicOnly or -LocalOnly, not both."
}

$EndpointPath = if ($Ready) { "/ready" } else { "/health" }

$targets = @()
if (-not $PublicOnly) {
    $targets += @(
        @{ Name = "DD local"; Url = "http://127.0.0.1:8000$EndpointPath" },
        @{ Name = "Injection local"; Url = "http://127.0.0.1:8010$EndpointPath" }
    )
}

if (-not $LocalOnly) {
    foreach ($baseUrl in $PublicBaseUrls) {
        $name = $baseUrl.Replace("https://", "").Replace("http://", "")
        $targets += @{ Name = "$name public"; Url = "$($baseUrl.TrimEnd('/'))$EndpointPath" }
    }
}

$failures = 0
foreach ($target in $targets) {
    $passed = $false
    $lastMessage = ""

    for ($attempt = 1; $attempt -le $Retries; $attempt++) {
        try {
            $response = Invoke-WebRequest -Uri $target.Url -UseBasicParsing -TimeoutSec 10
            $content = $response.Content.Trim()
            $isReady = $true
            if ($Ready) {
                try {
                    $json = $content | ConvertFrom-Json
                    $isReady = $json.status -eq "ready"
                } catch {
                    $isReady = $false
                }
            }

            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 300 -and $isReady) {
                Write-Host ("{0}: HTTP {1} {2}" -f $target.Name, $response.StatusCode, $content)
                $passed = $true
                break
            }

            $lastMessage = ("{0}: NOT READY HTTP {1} {2}" -f $target.Name, $response.StatusCode, $content)
        } catch {
            $lastMessage = ("{0}: FAILED {1}" -f $target.Name, $_.Exception.Message)
        }

        if ($attempt -lt $Retries) {
            Start-Sleep -Seconds $RetryDelaySec
        }
    }

    if (-not $passed) {
        $failures += 1
        Write-Host $lastMessage
    }
}

if ($Strict -and $failures -gt 0) {
    exit 1
}
