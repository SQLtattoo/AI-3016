# AI-3016 Demo Environment Activation (PowerShell)
Write-Host "🚀 Activating AI-3016 virtual environment..." -ForegroundColor Green

# Activate virtual environment
& .\ai3016-env\Scripts\Activate.ps1

Write-Host "✅ Virtual environment activated!" -ForegroundColor Green
Write-Host "📚 Available demos:" -ForegroundColor Yellow
Write-Host "   • python 3_chat_client_demo.py       (Chat client)" -ForegroundColor Cyan
Write-Host "   • python 2c_rag_api_demo.py          (RAG pattern)" -ForegroundColor Cyan
Write-Host "   • python 1b_fine_tuning_code_first.py (Fine-tuning)" -ForegroundColor Cyan
Write-Host ""
Write-Host "📖 Help: cat CLASS_DEMO_FLOW.md" -ForegroundColor Magenta
