$ErrorActionPreference = "Stop"

Write-Host "1/6 Checking Git status..."
git status

Write-Host "2/6 Checking tracked .env..."
$trackedEnv = git ls-files .env
if ($trackedEnv) {
    throw ".env is tracked by Git. Stop release."
}

Write-Host "3/6 Compiling src..."
py -B -m compileall src

Write-Host "4/6 Compiling tests..."
py -B -m compileall tests

Write-Host "5/6 Running tests..."
py -B -m unittest discover -s tests -v

Write-Host "6/6 Running main pipeline..."
py -B src\main_pipeline.py

Write-Host ""
Write-Host "RELEASE BASELINE PASS"
