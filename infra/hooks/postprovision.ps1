#!/usr/bin/env pwsh

# Post-provision script for AI-3016 demo environment
# This script uploads RAG source documents to Azure Storage after infrastructure deployment

Write-Host "Starting post-provision setup..." -ForegroundColor Green

# Ensure azd environment values are available (useful when running manually)
if (-not $env:AZURE_STORAGE_ACCOUNT_NAME) {
    Write-Host "Loading azd environment values..." -ForegroundColor Yellow
    $azdEnvOutput = azd env get-values 2>$null
    if ($LASTEXITCODE -eq 0 -and $azdEnvOutput) {
        $azdEnvOutput -split "`n" | ForEach-Object {
            $line = $_.Trim()
            if (-not [string]::IsNullOrWhiteSpace($line) -and -not $line.StartsWith('#')) {
                $parts = $line.Split('=', 2)
                if ($parts.Length -eq 2) {
                    [System.Environment]::SetEnvironmentVariable($parts[0], $parts[1])
                }
            }
        }
    } else {
        Write-Warning "Unable to load azd environment values."
    }
}

# Get environment variables from azd
$storageAccountName = $env:AZURE_STORAGE_ACCOUNT_NAME
$containerName = $env:AZURE_STORAGE_CONTAINER_NAME
$resourceGroup = $env:AZURE_RESOURCE_GROUP

if (-not $storageAccountName) {
    Write-Error "AZURE_STORAGE_ACCOUNT_NAME not found in environment"
    exit 1
}

Write-Host "Storage Account: $storageAccountName" -ForegroundColor Cyan
Write-Host "Container: $containerName" -ForegroundColor Cyan
Write-Host "Resource Group: $resourceGroup" -ForegroundColor Cyan

# Upload RAG source files to storage
$ragSourcesPath = Join-Path $PSScriptRoot "..\..\RAG-sources"

if (-not (Test-Path $ragSourcesPath)) {
    Write-Warning "RAG-sources directory not found at $ragSourcesPath"
    Write-Host "Skipping RAG sources upload..."
} else {
    Write-Host "`nUploading RAG source documents..." -ForegroundColor Green
    
    $files = Get-ChildItem -Path $ragSourcesPath -File
    
    foreach ($file in $files) {
        Write-Host "  Uploading $($file.Name)..." -ForegroundColor Yellow
        
        az storage blob upload `
            --account-name $storageAccountName `
            --container-name $containerName `
            --name $file.Name `
            --file $file.FullName `
            --auth-mode login `
            --overwrite
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "    ✓ Uploaded successfully" -ForegroundColor Green
        } else {
            Write-Warning "    ✗ Failed to upload $($file.Name)"
        }
    }
}

# Create .env file from outputs
Write-Host "`nCreating .env file from deployment outputs..." -ForegroundColor Green

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$envFilePath = Join-Path $repoRoot ".env"

$foundryServiceName = $env:AZURE_FOUNDRY_SERVICE_NAME
$searchServiceName = $env:AZURE_SEARCH_SERVICE_NAME

function Clean-EnvValue {
    param([string]$Value)

    if ([string]::IsNullOrWhiteSpace($Value)) {
        return ''
    }

    return $Value.Trim().Trim('"')
}

function Get-OrPlaceholder {
    param(
        [string]$Value,
        [string]$Placeholder
    )

    if ([string]::IsNullOrWhiteSpace($Value)) {
        return $Placeholder
    }

    return Clean-EnvValue $Value
}

$foundryApiKey = ""
if ($foundryServiceName -and $resourceGroup) {
    $foundryApiKey = az cognitiveservices account keys list `
        --name $foundryServiceName `
        --resource-group $resourceGroup `
        --query "key1" -o tsv 2>$null

    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($foundryApiKey)) {
        Write-Warning "Unable to retrieve Microsoft Foundry key automatically."
        $foundryApiKey = "REPLACE_WITH_FOUNDATION_KEY"
    } else {
        $foundryApiKey = $foundryApiKey.Trim()
    }
} else {
    Write-Warning "AZURE_FOUNDRY_SERVICE_NAME or AZURE_RESOURCE_GROUP missing; cannot fetch key."
    $foundryApiKey = "REPLACE_WITH_FOUNDATION_KEY"
}

$searchAdminKey = ""
if ($searchServiceName -and $resourceGroup) {
    $searchAdminKey = az search admin-key show `
        --service-name $searchServiceName `
        --resource-group $resourceGroup `
        --query "primaryKey" -o tsv 2>$null

    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($searchAdminKey)) {
        Write-Warning "Unable to retrieve Azure AI Search admin key automatically."
        $searchAdminKey = "REPLACE_WITH_SEARCH_KEY"
    } else {
        $searchAdminKey = $searchAdminKey.Trim()
    }
} else {
    Write-Warning "AZURE_SEARCH_SERVICE_NAME or AZURE_RESOURCE_GROUP missing; cannot fetch search key."
    $searchAdminKey = "REPLACE_WITH_SEARCH_KEY"
}

$endpointUrl = Get-OrPlaceholder -Value $env:AZURE_OPENAI_ENDPOINT -Placeholder "https://your-ai-foundry.cognitiveservices.azure.com/"
$deploymentName = Get-OrPlaceholder -Value $env:AZURE_OPENAI_DEPLOYMENT_NAME -Placeholder "gpt-4o"

# Get the embeddings deployment details from the Foundry resource
$embeddingsServiceName = $env:AZURE_OPENAI_EMBEDDINGS_SERVICE_NAME
$embeddingsEndpoint = Clean-EnvValue $env:AZURE_OPENAI_EMBEDDINGS_ENDPOINT
$embeddingsDeployment = Clean-EnvValue $env:AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT_NAME
$embeddingsApiKey = ""

if ($embeddingsServiceName -and $resourceGroup) {
    $embeddingsApiKey = az cognitiveservices account keys list `
        --name $embeddingsServiceName `
        --resource-group $resourceGroup `
        --query "key1" -o tsv 2>$null
    
    if ($LASTEXITCODE -eq 0 -and $embeddingsApiKey) {
        $embeddingsApiKey = $embeddingsApiKey.Trim()
    }
}

$searchEndpoint = Clean-EnvValue $env:AZURE_SEARCH_ENDPOINT
$storageAccountNameClean = Clean-EnvValue $env:AZURE_STORAGE_ACCOUNT_NAME
$storageContainerNameClean = Clean-EnvValue $env:AZURE_STORAGE_CONTAINER_NAME
$storageEndpointClean = Clean-EnvValue $env:AZURE_STORAGE_ENDPOINT
$resourceGroupClean = Clean-EnvValue $env:AZURE_RESOURCE_GROUP
$locationClean = Clean-EnvValue $env:AZURE_LOCATION
$tenantClean = Clean-EnvValue $env:AZURE_TENANT_ID
$projectEndpointClean = Clean-EnvValue $env:AZURE_AI_PROJECT_ENDPOINT
$keyVaultNameClean = Clean-EnvValue $env:AZURE_KEY_VAULT_NAME
$keyVaultUriClean = Clean-EnvValue $env:AZURE_KEY_VAULT_URI

$envContent = @"
# AI-3016 Environment Configuration
# Generated by azd post-provision hook on $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')

# Microsoft Foundry Configuration
ENDPOINT_URL=$endpointUrl
DEPLOYMENT_NAME=$deploymentName
AZURE_AI_FOUNDRY_API_KEY=$foundryApiKey

# Microsoft Foundry Project
AZURE_AI_PROJECT_NAME=$(Clean-EnvValue $env:AZURE_AI_PROJECT_NAME)
AZURE_AI_PROJECT_ENDPOINT=$projectEndpointClean
AZURE_SUBSCRIPTION_ID=$(az account show --query id -o tsv 2>$null | ForEach-Object { $_.Trim() })
AZURE_AI_AUTH_MODE=entra

# Azure OpenAI-compatible variables for the Foundry resource
AZURE_OPENAI_ENDPOINT=$embeddingsEndpoint
AZURE_OPENAI_API_KEY=$embeddingsApiKey
AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT_NAME=$embeddingsDeployment

# Azure AI Search Configuration
AZURE_SEARCH_ENDPOINT=$searchEndpoint
AZURE_SEARCH_ADMIN_KEY=$searchAdminKey
AZURE_SEARCH_INDEX=rag-bank-documents

# Storage (used by docs + troubleshooting)
AZURE_STORAGE_ACCOUNT_NAME=$storageAccountNameClean
AZURE_STORAGE_CONTAINER_NAME=$storageContainerNameClean
AZURE_STORAGE_ENDPOINT=$storageEndpointClean

# Key Vault
AZURE_KEY_VAULT_NAME=$keyVaultNameClean
AZURE_KEY_VAULT_URI=$keyVaultUriClean

# General Azure context
AZURE_RESOURCE_GROUP=$resourceGroupClean
AZURE_LOCATION=$locationClean
AZURE_TENANT_ID=$tenantClean
"@

$envContent | Out-File -FilePath $envFilePath -Encoding UTF8 -Force

Write-Host "✓ .env file created at: $envFilePath" -ForegroundColor Green

# Store secrets in Key Vault
$keyVaultName = Clean-EnvValue $env:AZURE_KEY_VAULT_NAME

if ($keyVaultName) {
    Write-Host "`n🔐 Storing secrets in Azure Key Vault..." -ForegroundColor Green
    
    # Store Foundry API Key
    if ($foundryApiKey -and $foundryApiKey -ne "REPLACE_WITH_FOUNDATION_KEY") {
        Write-Host "   Storing AZURE-AI-FOUNDRY-API-KEY..." -ForegroundColor Yellow
        az keyvault secret set --vault-name $keyVaultName --name "AZURE-AI-FOUNDRY-API-KEY" --value $foundryApiKey --output none 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "   ✓ Stored successfully" -ForegroundColor Green
        }
    }
    
    # Store OpenAI API Key
    if ($embeddingsApiKey) {
        Write-Host "   Storing AZURE-OPENAI-API-KEY..." -ForegroundColor Yellow
        az keyvault secret set --vault-name $keyVaultName --name "AZURE-OPENAI-API-KEY" --value $embeddingsApiKey --output none 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "   ✓ Stored successfully" -ForegroundColor Green
        }
    }
    
    # Store Search Admin Key
    if ($searchAdminKey -and $searchAdminKey -ne "REPLACE_WITH_SEARCH_KEY") {
        Write-Host "   Storing AZURE-SEARCH-ADMIN-KEY..." -ForegroundColor Yellow
        az keyvault secret set --vault-name $keyVaultName --name "AZURE-SEARCH-ADMIN-KEY" --value $searchAdminKey --output none 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "   ✓ Stored successfully" -ForegroundColor Green
        }
    }
    
    # Store endpoints and deployment names (not sensitive but useful)
    az keyvault secret set --vault-name $keyVaultName --name "ENDPOINT-URL" --value $endpointUrl --output none 2>$null
    az keyvault secret set --vault-name $keyVaultName --name "AZURE-OPENAI-ENDPOINT" --value $embeddingsEndpoint --output none 2>$null
    az keyvault secret set --vault-name $keyVaultName --name "AZURE-SEARCH-ENDPOINT" --value $searchEndpoint --output none 2>$null
    
    Write-Host "   ✓ Key Vault setup complete" -ForegroundColor Green
    Write-Host "   Key Vault: $keyVaultName" -ForegroundColor Cyan
} else {
    Write-Warning "Key Vault name not found. Secrets not stored in Key Vault."
}

# Create Azure AI Search index and upload documents
Write-Host "`n📊 Setting up Azure AI Search index..." -ForegroundColor Green

$pythonExe = Join-Path $repoRoot "ai3016-env\Scripts\python.exe"
$setupScript = Join-Path $repoRoot "setup_search_index.py"

if (Test-Path $pythonExe) {
    if (Test-Path $setupScript) {
        Write-Host "   Running search index setup..." -ForegroundColor Yellow
        & $pythonExe $setupScript
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "   ✓ Search index setup completed" -ForegroundColor Green
        } else {
            Write-Warning "   Search index setup encountered issues. You can run it manually:"
            Write-Warning "   python setup_search_index.py"
        }
    } else {
        Write-Warning "setup_search_index.py not found. Run manually after setup."
    }
} else {
    Write-Warning "Python environment not found. Please run:"
    Write-Warning "  1. python -m venv ai3016-env"
    Write-Warning "  2. .\ai3016-env\Scripts\Activate.ps1"
    Write-Warning "  3. pip install -r requirements.txt"
    Write-Warning "  4. python setup_search_index.py"
}

Write-Host "`nPost-provision setup complete!" -ForegroundColor Green
Write-Host "`nYour AI-3016 demo environment is ready to use!" -ForegroundColor Cyan
Write-Host "`nNext steps:" -ForegroundColor Yellow
Write-Host "  1. Activate your Python environment: .\activate_env.ps1" -ForegroundColor White
Write-Host "  2. Run the concept demo: python 0_concept_demo.py" -ForegroundColor White
Write-Host "  3. Try the RAG demo: python 2c_rag_api_demo.py" -ForegroundColor White
Write-Host "  4. Start the chat client: python 3_chat_client_demo.py" -ForegroundColor White
