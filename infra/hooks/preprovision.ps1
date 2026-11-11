#!/usr/bin/env pwsh
$ErrorActionPreference = 'Stop'
& python (Join-Path $PSScriptRoot 'provision.py') preprovision @args
exit $LASTEXITCODE
