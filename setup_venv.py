"""
Virtual Environment Setup for AI-3016 Demos
==========================================

This script creates and configures a Python virtual environment
for the AI-3016 demos to keep dependencies isolated.
"""

import os
import sys
import subprocess
import platform
from pathlib import Path

def create_virtual_environment():
    """Create a Python virtual environment"""
    print("🐍 Creating Python virtual environment...")
    
    venv_name = "ai3016-env"
    
    try:
        # Create virtual environment
        subprocess.check_call([
            sys.executable, "-m", "venv", venv_name
        ])
        print(f"✅ Virtual environment '{venv_name}' created successfully!")
        return venv_name
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to create virtual environment: {e}")
        return None

def get_activation_command(venv_name):
    """Get the correct activation command for the current OS"""
    if platform.system() == "Windows":
        return f"{venv_name}\\Scripts\\Activate.ps1"
    else:
        return f"source {venv_name}/bin/activate"

def install_requirements_in_venv(venv_name):
    """Install requirements in the virtual environment"""
    print("📦 Installing requirements in virtual environment...")
    
    # Get the correct python executable for the venv
    if platform.system() == "Windows":
        python_exe = os.path.join(venv_name, "Scripts", "python.exe")
        pip_exe = os.path.join(venv_name, "Scripts", "pip.exe")
    else:
        python_exe = os.path.join(venv_name, "bin", "python")
        pip_exe = os.path.join(venv_name, "bin", "pip")
    
    try:
        # Upgrade pip first
        subprocess.check_call([python_exe, "-m", "pip", "install", "--upgrade", "pip"])
        
        # Install requirements
        subprocess.check_call([pip_exe, "install", "-r", "requirements.txt"])
        
        print("✅ Requirements installed successfully in virtual environment!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install requirements: {e}")
        return False

def create_activation_scripts():
    """Create convenient activation scripts for different shells"""
    print("📝 Creating activation scripts...")
    
    # PowerShell activation script
    ps1_content = """# AI-3016 Demo Environment Activation (PowerShell)
Write-Host "🚀 Activating AI-3016 virtual environment..." -ForegroundColor Green

# Activate virtual environment
& .\\ai3016-env\\Scripts\\Activate.ps1

Write-Host "✅ Virtual environment activated!" -ForegroundColor Green
Write-Host "📚 Available demos:" -ForegroundColor Yellow
Write-Host "   • python 0_concept_demo.py      (Concept overview)" -ForegroundColor Cyan
Write-Host "   • python 1_fine_tuning_demo.py  (Fine-tuning demo)" -ForegroundColor Cyan  
Write-Host "   • python 2_rag_pattern_demo.py  (RAG pattern demo)" -ForegroundColor Cyan
Write-Host ""
Write-Host "🔧 Setup: python setup_demo.py" -ForegroundColor Magenta
Write-Host "📖 Help: cat README.md" -ForegroundColor Magenta
"""
    
    with open("activate_env.ps1", "w", encoding="utf-8") as f:
        f.write(ps1_content)
    
    # Batch file for Command Prompt
    bat_content = """@echo off
echo 🚀 Activating AI-3016 virtual environment...
call ai3016-env\\Scripts\\activate.bat
echo ✅ Virtual environment activated!
echo 📚 Available demos:
echo    • python 0_concept_demo.py      (Concept overview)
echo    • python 1_fine_tuning_demo.py  (Fine-tuning demo)
echo    • python 2_rag_pattern_demo.py  (RAG pattern demo)
echo.
echo 🔧 Setup: python setup_demo.py
echo 📖 Help: type README.md
"""
    
    with open("activate_env.bat", "w", encoding="utf-8") as f:
        f.write(bat_content)
    
    # Bash script for Linux/Mac
    bash_content = """#!/bin/bash
echo "🚀 Activating AI-3016 virtual environment..."
source ai3016-env/bin/activate
echo "✅ Virtual environment activated!"
echo "📚 Available demos:"
echo "   • python 0_concept_demo.py      (Concept overview)"
echo "   • python 1_fine_tuning_demo.py  (Fine-tuning demo)"
echo "   • python 2_rag_pattern_demo.py  (RAG pattern demo)"
echo ""
echo "🔧 Setup: python setup_demo.py"
echo "📖 Help: cat README.md"
"""
    
    with open("activate_env.sh", "w", encoding="utf-8") as f:
        f.write(bash_content)
    
    # Make bash script executable on Unix systems
    if platform.system() != "Windows":
        os.chmod("activate_env.sh", 0o755)
    
    print("✅ Activation scripts created:")
    print("   • activate_env.ps1 (PowerShell)")
    print("   • activate_env.bat (Command Prompt)")
    print("   • activate_env.sh (Bash/Linux/Mac)")

def update_gitignore():
    """Create/update .gitignore to exclude virtual environment"""
    print("📝 Creating .gitignore...")
    
    gitignore_content = """# AI-3016 Demo .gitignore

# Virtual Environment
ai3016-env/
venv/
env/

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Environment Variables
.env
.env.local
.env.development
.env.test
.env.production

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Logs
*.log

# Azure
.azure/

# Jupyter
.ipynb_checkpoints/
"""
    
    with open(".gitignore", "w", encoding="utf-8") as f:
        f.write(gitignore_content)
    
    print("✅ .gitignore created")

def display_next_steps(venv_name):
    """Display next steps for the user"""
    activation_cmd = get_activation_command(venv_name)
    
    print("\n" + "="*60)
    print("🎉 Virtual Environment Setup Complete!")
    print("="*60)
    
    print(f"\n🚀 To activate the virtual environment:")
    if platform.system() == "Windows":
        print(f"   PowerShell: .\\activate_env.ps1")
        print(f"   Command Prompt: activate_env.bat")
        print(f"   Manual: {activation_cmd}")
    else:
        print(f"   Bash: ./activate_env.sh")
        print(f"   Manual: {activation_cmd}")
    
    print(f"\n📚 Once activated, run the demos:")
    print(f"   • python 0_concept_demo.py      (Concept overview)")
    print(f"   • python 1_fine_tuning_demo.py  (Fine-tuning demo)")
    print(f"   • python 2_rag_pattern_demo.py  (RAG pattern demo)")
    
    print(f"\n🔧 Setup Azure resources:")
    print(f"   • python setup_demo.py")
    
    print(f"\n💡 Pro Tips:")
    print(f"   • Always activate the virtual environment before running demos")
    print(f"   • Use 'deactivate' command to exit the virtual environment")
    print(f"   • The virtual environment is in the '{venv_name}' folder")
    
    print(f"\n📖 For more details, see README.md")

def main():
    """Main setup function"""
    print("🎬 AI-3016 Virtual Environment Setup")
    print("=" * 40)
    
    # Check if virtual environment already exists
    venv_name = "ai3016-env"
    if os.path.exists(venv_name):
        print(f"⚠️  Virtual environment '{venv_name}' already exists!")
        response = input("Do you want to recreate it? (y/N): ").strip().lower()
        if response == 'y':
            print("🗑️  Removing existing virtual environment...")
            import shutil
            shutil.rmtree(venv_name)
        else:
            print("✅ Using existing virtual environment")
            display_next_steps(venv_name)
            return
    
    # Create virtual environment
    venv_name = create_virtual_environment()
    if not venv_name:
        return
    
    # Install requirements
    if not install_requirements_in_venv(venv_name):
        return
    
    # Create activation scripts
    create_activation_scripts()
    
    # Create .gitignore
    update_gitignore()
    
    # Display next steps
    display_next_steps(venv_name)

if __name__ == "__main__":
    main()