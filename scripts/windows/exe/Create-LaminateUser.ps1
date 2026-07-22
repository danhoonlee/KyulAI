param(
    [Parameter(Mandatory = $true)]
    [string]$Email,
    [Parameter(Mandatory = $true)]
    [string]$Password,
    [string]$Name = "",
    [string]$AuthDbPath = ".\data\imperialax_auth.sqlite3"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path ".\.venv")) {
    py -3.11 -m venv .venv
}

& ".\.venv\Scripts\Activate.ps1"
python -m pip install --upgrade pip | Out-Null
pip install -r ".\requirements-serving.txt" | Out-Null

$AuthDbParent = Split-Path -Parent $AuthDbPath
if (-not $AuthDbParent) {
    $AuthDbParent = "."
}
New-Item -ItemType Directory -Force -Path $AuthDbParent | Out-Null
$env:IMPERIALAX_AUTH_DB_PATH = (Join-Path (Resolve-Path $AuthDbParent).Path (Split-Path -Leaf $AuthDbPath))

python -c @"
from src.backend.services.imperialax_auth_store import create_account_by_admin, DuplicateAccountError

email = r'''$Email'''
password = r'''$Password'''
name = r'''$Name''' or email.split('@')[0]

try:
    user = create_account_by_admin(
        email=email,
        password=password,
        name=name,
        entitlements=('module.laminate',),
    )
    print(f'Created Laminate user: {user.email}')
except DuplicateAccountError:
    print(f'User already exists: {email.lower()}')
"@

Write-Host "Auth DB: $env:IMPERIALAX_AUTH_DB_PATH" -ForegroundColor Green
