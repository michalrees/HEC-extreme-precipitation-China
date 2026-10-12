$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    & xelatex -interaction=nonstopmode -halt-on-error manuscript.tex
    if ($LASTEXITCODE -ne 0) { throw 'First XeLaTeX pass failed.' }
    & bibtex manuscript
    if ($LASTEXITCODE -ne 0) { throw 'BibTeX failed.' }
    & xelatex -interaction=nonstopmode -halt-on-error manuscript.tex
    if ($LASTEXITCODE -ne 0) { throw 'Second XeLaTeX pass failed.' }
    & xelatex -interaction=nonstopmode -halt-on-error manuscript.tex
    if ($LASTEXITCODE -ne 0) { throw 'Final XeLaTeX pass failed.' }
} finally {
    Pop-Location
}
