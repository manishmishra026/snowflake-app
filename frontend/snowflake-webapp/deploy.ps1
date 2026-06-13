# deploy.ps1
# Usage: .\deploy.ps1 -ResourceGroup "myResourceGroup" -AppName "myAppService"

param (
    [Parameter(Mandatory=$true)]
    [string]$ResourceGroup="mmrg",

    [Parameter(Mandatory=$true)]
    [string]$AppName ="mmappservice-testappgw"
)

$ErrorActionPreference = "Stop"

Write-Host "1. Installing frontend dependencies..." -ForegroundColor Cyan
npm install

Write-Host "2. Building Angular application..." -ForegroundColor Cyan
npm run build

# Path to built static files
$buildOutPath = ".\dist\snowflake-webapp\browser"
$zipPath = ".\deploy.zip"

if (Test-Path $zipPath) {
    Remove-Item $zipPath -Force
}

Write-Host "3. Compressing build outputs into $zipPath..." -ForegroundColor Cyan
# Compress only the files inside the browser folder, not the folder itself
Compress-Archive -Path "$buildOutPath\*" -DestinationPath $zipPath -Force

Write-Host "4. Disabling Oryx build on App Service (since we deploy pre-built static files)..." -ForegroundColor Cyan
az webapp config appsettings set --resource-group $ResourceGroup --name $AppName --settings SCM_DO_BUILD_DURING_DEPLOYMENT=false

Write-Host "5. Deploying to Azure App Service via Zip Push Deploy..." -ForegroundColor Cyan
az webapp deploy --resource-group $ResourceGroup --name $AppName --src-path $zipPath --type zip

Write-Host "6. Configuring App Service Startup Command for PM2 SPA serving..." -ForegroundColor Cyan
# Since we are zipping only the build output (index.html, js, css files),
# they will be extracted directly into /home/site/wwwroot.
# We instruct PM2 to serve /home/site/wwwroot in SPA mode.
az webapp config set --resource-group $ResourceGroup --name $AppName --startup-file "pm2 serve /home/site/wwwroot --no-daemon --spa"

Write-Host "Deployment completed successfully!" -ForegroundColor Green
