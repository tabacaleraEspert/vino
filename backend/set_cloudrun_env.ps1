# Lee el .env y sube las variables a Cloud Run
$gcloud = "$env:LOCALAPPDATA\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"
$envFile = "$PSScriptRoot\.env"

# Variables a incluir en Cloud Run (excluir las de SQL Server legacy)
$include = @(
    "JWT_SECRET", "MASTER_KEY", "DATABASE_URL", "OPENAI_API_KEY",
    "GOOGLE_CLIENT_ID", "GOOGLE_IOS_CLIENT_ID", "GOOGLE_CLIENT_SECRET",
    "GMAIL_TOKEN_KEY", "TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN",
    "TWILIO_WHATSAPP_FROM", "TWILIO_OTP_CONTENT_SID", "TWILIO_REMINDER_CONTENT_SID"
)

# Parse .env file
$envVars = @{}
Get-Content $envFile | ForEach-Object {
    $line = $_.Trim()
    if ($line -and -not $line.StartsWith("#")) {
        $idx = $line.IndexOf("=")
        if ($idx -gt 0) {
            $key = $line.Substring(0, $idx).Trim()
            $val = $line.Substring($idx + 1).Trim()
            if ($include -contains $key) {
                $envVars[$key] = $val
            }
        }
    }
}

# Build env vars string (escape commas in values)
$parts = $envVars.GetEnumerator() | ForEach-Object {
    "$($_.Key)=$($_.Value)"
}
$envString = $parts -join ","

Write-Host "Configurando $($envVars.Count) variables en Cloud Run..."
& $gcloud run services update ahorros-backend `
    --region us-central1 `
    --set-env-vars $envString `
    --quiet 2>&1

Write-Host "Listo. Exit: $LASTEXITCODE"
