#!/usr/bin/env pwsh
$ErrorActionPreference = 'Stop'
& python (Join-Path $PSScriptRoot 'provision.py') postprovision @args
exit $LASTEXITCODE
