<#
.SYNOPSIS
    Build and push Docker images for AIGalileoArena to GHCR.

.DESCRIPTION
    Builds backend (with ONNX models) and frontend (with NEXT_PUBLIC_* baked in)
    Docker images, then pushes them to GitHub Container Registry.

.PARAMETER Registry
    Container registry prefix (default: ghcr.io/ateetvatan)

.PARAMETER BackendUrl
    Public URL of the backend service on Railway (required for frontend build)

.PARAMETER AdminApiKey
    Admin API key to bake into the frontend (optional)

.PARAMETER Tag
    Image tag (default: latest)

.PARAMETER SkipBackend
    Skip backend build/push

.PARAMETER SkipFrontend
    Skip frontend build/push

.EXAMPLE
    .\deploy.ps1 -BackendUrl "https://galileo-backend.up.railway.app"
    .\deploy.ps1 -BackendUrl "https://galileo-backend.up.railway.app" -SkipFrontend
#>
param(
    [string]$Registry = "ghcr.io/ateetvatan",
    [Parameter(Mandatory=$true)]
    [string]$BackendUrl,
    [string]$AdminApiKey = "",
    [string]$Tag = "latest",
    [switch]$SkipBackend,
    [switch]$SkipFrontend
)

$ErrorActionPreference = "Stop"

Write-Host "`n=== AIGalileoArena Deploy ===" -ForegroundColor Cyan

# ---- Backend ----
if (-not $SkipBackend) {
    $backendImage = "${Registry}/galileo-backend:${Tag}"
    Write-Host "`n[1/4] Building backend image..." -ForegroundColor Yellow
    docker build -t $backendImage ./backend
    if ($LASTEXITCODE -ne 0) { throw "Backend build failed" }

    Write-Host "[2/4] Pushing backend image..." -ForegroundColor Yellow
    docker push $backendImage
    if ($LASTEXITCODE -ne 0) { throw "Backend push failed" }

    Write-Host "Backend: $backendImage" -ForegroundColor Green
} else {
    Write-Host "`n[1-2/4] Skipping backend" -ForegroundColor DarkGray
}

# ---- Frontend ----
if (-not $SkipFrontend) {
    $frontendImage = "${Registry}/galileo-frontend:${Tag}"
    Write-Host "`n[3/4] Building frontend image..." -ForegroundColor Yellow
    docker build `
        --build-arg NEXT_PUBLIC_API_URL=$BackendUrl `
        --build-arg NEXT_PUBLIC_ADMIN_API_KEY=$AdminApiKey `
        -t $frontendImage ./frontend
    if ($LASTEXITCODE -ne 0) { throw "Frontend build failed" }

    Write-Host "[4/4] Pushing frontend image..." -ForegroundColor Yellow
    docker push $frontendImage
    if ($LASTEXITCODE -ne 0) { throw "Frontend push failed" }

    Write-Host "Frontend: $frontendImage" -ForegroundColor Green
} else {
    Write-Host "`n[3-4/4] Skipping frontend" -ForegroundColor DarkGray
}

Write-Host "`n=== Done! ===" -ForegroundColor Cyan
Write-Host "Now redeploy both services in Railway to pull the new images.`n"
