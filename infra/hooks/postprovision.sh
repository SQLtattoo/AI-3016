#!/bin/bash

# Post-provision script for AI-3016 demo environment
# This script uploads RAG source documents to Azure Storage after infrastructure deployment

echo "Starting post-provision setup..."

# Ensure azd environment values are available (useful when running manually)
if [ -z "$AZURE_STORAGE_ACCOUNT_NAME" ]; then
    echo "Loading azd environment values..."
    AZD_ENV_OUTPUT=$(azd env get-values 2>/dev/null)
    if [ $? -eq 0 ] && [ -n "$AZD_ENV_OUTPUT" ]; then
        while IFS= read -r line; do
            trimmed="$(echo "$line" | xargs)"
            if [ -n "$trimmed" ] && [[ ! "$trimmed" =~ ^# ]]; then
                var_name="${trimmed%%=*}"
                var_value="${trimmed#*=}"
                export "$var_name"="$var_value"
            fi
        done <<< "$AZD_ENV_OUTPUT"
    else
        echo "Warning: Unable to load azd environment values."
    fi
fi

# Get environment variables from azd
STORAGE_ACCOUNT_NAME="${AZURE_STORAGE_ACCOUNT_NAME}"
CONTAINER_NAME="${AZURE_STORAGE_CONTAINER_NAME}"
RESOURCE_GROUP="${AZURE_RESOURCE_GROUP}"

strip_quotes() {
    local value="$1"
    value="${value%\"}"
    value="${value#\"}"
    echo "$value"
}

if [ -z "$STORAGE_ACCOUNT_NAME" ]; then
    echo "Error: AZURE_STORAGE_ACCOUNT_NAME not found in environment"
    exit 1
fi

echo "Storage Account: $STORAGE_ACCOUNT_NAME"
echo "Container: $CONTAINER_NAME"
echo "Resource Group: $RESOURCE_GROUP"

# Upload RAG source files to storage
RAG_SOURCES_PATH="$(dirname "$0")/../../RAG-sources"

if [ ! -d "$RAG_SOURCES_PATH" ]; then
    echo "Warning: RAG-sources directory not found at $RAG_SOURCES_PATH"
    echo "Skipping RAG sources upload..."
else
    echo ""
    echo "Uploading RAG source documents..."
    
    for file in "$RAG_SOURCES_PATH"/*; do
        if [ -f "$file" ]; then
            filename=$(basename "$file")
            echo "  Uploading $filename..."
            
            az storage blob upload \
                --account-name "$STORAGE_ACCOUNT_NAME" \
                --container-name "$CONTAINER_NAME" \
                --name "$filename" \
                --file "$file" \
                --auth-mode login \
                --overwrite
            
            if [ $? -eq 0 ]; then
                echo "    ✓ Uploaded successfully"
            else
                echo "    ✗ Failed to upload $filename"
            fi
        fi
    done
fi

# Create .env file from outputs
echo ""
echo "Creating .env file from deployment outputs..."

ENV_FILE="$(dirname "$0")/../../.env"

FOUNDATION_KEY="REPLACE_WITH_FOUNDATION_KEY"
if [ -n "$AZURE_FOUNDRY_SERVICE_NAME" ] && [ -n "$AZURE_RESOURCE_GROUP" ]; then
    FOUNDATION_KEY=$(az cognitiveservices account keys list \
        --name "$AZURE_FOUNDRY_SERVICE_NAME" \
        --resource-group "$AZURE_RESOURCE_GROUP" \
        --query "key1" -o tsv 2>/dev/null)

    if [ -z "$FOUNDATION_KEY" ]; then
        echo "Warning: Unable to retrieve Microsoft Foundry key automatically."
        FOUNDATION_KEY="REPLACE_WITH_FOUNDATION_KEY"
    fi
else
    echo "Warning: Missing AZURE_FOUNDRY_SERVICE_NAME or AZURE_RESOURCE_GROUP; cannot fetch Foundry key."
fi

SEARCH_ADMIN_KEY="REPLACE_WITH_SEARCH_KEY"
if [ -n "$AZURE_SEARCH_SERVICE_NAME" ] && [ -n "$AZURE_RESOURCE_GROUP" ]; then
    SEARCH_ADMIN_KEY=$(az search admin-key show \
        --service-name "$AZURE_SEARCH_SERVICE_NAME" \
        --resource-group "$AZURE_RESOURCE_GROUP" \
        --query "primaryKey" -o tsv 2>/dev/null)

    if [ -z "$SEARCH_ADMIN_KEY" ]; then
        echo "Warning: Unable to retrieve Azure AI Search admin key automatically."
        SEARCH_ADMIN_KEY="REPLACE_WITH_SEARCH_KEY"
    fi
else
    echo "Warning: Missing AZURE_SEARCH_SERVICE_NAME or AZURE_RESOURCE_GROUP; cannot fetch search key."
fi

ENDPOINT_VALUE=$(strip_quotes "${AZURE_OPENAI_ENDPOINT:-https://your-ai-foundry.cognitiveservices.azure.com/}")
DEPLOYMENT_VALUE=$(strip_quotes "${AZURE_OPENAI_DEPLOYMENT_NAME:-gpt-4o}")

# Get separate OpenAI service details for embeddings
EMBEDDINGS_SERVICE_NAME="${AZURE_OPENAI_EMBEDDINGS_SERVICE_NAME}"
EMBEDDINGS_ENDPOINT=$(strip_quotes "${AZURE_OPENAI_EMBEDDINGS_ENDPOINT}")
EMBEDDINGS_DEPLOYMENT=$(strip_quotes "${AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT_NAME}")
EMBEDDINGS_API_KEY=""

if [ -n "$EMBEDDINGS_SERVICE_NAME" ] && [ -n "$AZURE_RESOURCE_GROUP" ]; then
    EMBEDDINGS_API_KEY=$(az cognitiveservices account keys list \
        --name "$EMBEDDINGS_SERVICE_NAME" \
        --resource-group "$AZURE_RESOURCE_GROUP" \
        --query "key1" -o tsv 2>/dev/null)
fi

SEARCH_ENDPOINT_VALUE=$(strip_quotes "${AZURE_SEARCH_ENDPOINT}")
STORAGE_ACCOUNT_VALUE=$(strip_quotes "${AZURE_STORAGE_ACCOUNT_NAME}")
STORAGE_CONTAINER_VALUE=$(strip_quotes "${AZURE_STORAGE_CONTAINER_NAME}")
STORAGE_ENDPOINT_VALUE=$(strip_quotes "${AZURE_STORAGE_ENDPOINT}")
RESOURCE_GROUP_VALUE=$(strip_quotes "${AZURE_RESOURCE_GROUP}")
LOCATION_VALUE=$(strip_quotes "${AZURE_LOCATION}")
TENANT_VALUE=$(strip_quotes "${AZURE_TENANT_ID}")

cat > "$ENV_FILE" << EOF
# AI-3016 Environment Configuration
# Generated by azd post-provision hook on $(date '+%Y-%m-%d %H:%M:%S')

# Microsoft Foundry Configuration
ENDPOINT_URL=$ENDPOINT_VALUE
DEPLOYMENT_NAME=$DEPLOYMENT_VALUE
AZURE_AI_FOUNDRY_API_KEY=$FOUNDATION_KEY

# Microsoft Foundry Project
AZURE_AI_PROJECT_NAME=$(strip_quotes "${AZURE_AI_PROJECT_NAME}")
AZURE_SUBSCRIPTION_ID=$(az account show --query id -o tsv 2>/dev/null | xargs)

# Azure OpenAI-compatible variables for the Foundry resource
AZURE_OPENAI_ENDPOINT=$EMBEDDINGS_ENDPOINT
AZURE_OPENAI_API_KEY=$EMBEDDINGS_API_KEY
AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT_NAME=$EMBEDDINGS_DEPLOYMENT

# Azure AI Search Configuration
AZURE_SEARCH_ENDPOINT=$SEARCH_ENDPOINT_VALUE
AZURE_SEARCH_ADMIN_KEY=$SEARCH_ADMIN_KEY
AZURE_SEARCH_INDEX=rag-bank-documents

# Storage (used by docs + troubleshooting)
AZURE_STORAGE_ACCOUNT_NAME=$STORAGE_ACCOUNT_VALUE
AZURE_STORAGE_CONTAINER_NAME=$STORAGE_CONTAINER_VALUE
AZURE_STORAGE_ENDPOINT=$STORAGE_ENDPOINT_VALUE

# General Azure context
AZURE_RESOURCE_GROUP=$RESOURCE_GROUP_VALUE
AZURE_LOCATION=$LOCATION_VALUE
AZURE_TENANT_ID=$TENANT_VALUE
EOF

echo "✓ .env file created at: $ENV_FILE"

# Create Azure AI Search index and upload documents
echo ""
echo "📊 Setting up Azure AI Search index..."

REPO_ROOT="$(dirname "$0")/../.."
PYTHON_EXE="$REPO_ROOT/ai3016-env/bin/python"
SETUP_SCRIPT="$REPO_ROOT/setup_search_index.py"

if [ -f "$PYTHON_EXE" ]; then
    if [ -f "$SETUP_SCRIPT" ]; then
        echo "   Running search index setup..."
        "$PYTHON_EXE" "$SETUP_SCRIPT"
        
        if [ $? -eq 0 ]; then
            echo "   ✓ Search index setup completed"
        else
            echo "Warning: Search index setup encountered issues. You can run it manually:"
            echo "   python setup_search_index.py"
        fi
    else
        echo "Warning: setup_search_index.py not found. Run manually after setup."
    fi
else
    echo "Warning: Python environment not found. Please run:"
    echo "  1. python -m venv ai3016-env"
    echo "  2. source ai3016-env/bin/activate"
    echo "  3. pip install -r requirements.txt"
    echo "  4. python setup_search_index.py"
fi

echo ""
echo "Post-provision setup complete!"
echo ""
echo "Your AI-3016 demo environment is ready to use!"
echo ""
echo "Next steps:"
echo "  1. Activate your Python environment: source activate_env.sh"
echo "  2. Run the concept demo: python 0_concept_demo.py"
echo "  3. Try the RAG demo: python 2c_rag_api_demo.py"
echo "  4. Start the chat client: python 3_chat_client_demo.py"
