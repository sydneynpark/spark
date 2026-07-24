# Single command to deploy any combination of spark.wiki's projects.
#
# Usage:
#   .\deploy.ps1 frontend backend
#   .\deploy.ps1 UpdatePhotoMetadata
#
# All the actual work happens in deploy.py; this just forwards arguments so
# the command matches this repo's other root-level scripts (start_local.ps1).

param(
    [Parameter(Mandatory, Position = 0, ValueFromRemainingArguments)]
    [string[]]$Targets
)

python "$PSScriptRoot\deploy.py" @Targets
