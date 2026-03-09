# Claude Code Instructions

## Quality Standards
- Always double-check your work before declaring something fixed
- Approach problems like an expert software engineer — understand root causes, don't just patch symptoms
- Test changes before pushing — use the VNC preview (`bash run_preview.sh`) to verify GUI changes work
- Only push after verifying the fix actually works

## Development Workflow
- Code in Codespaces, build via GitHub Actions
- To release: `git tag vX.Y && git push --tags` — auto-builds Windows .exe and publishes to GitHub Releases
- To test GUI locally: `bash run_preview.sh` → open port 6080 → append `/vnc.html`

## Project
- Entry point: `gui.py` (not `app.py`)
- Python GUI app using CustomTkinter
- Key deps: customtkinter, Pillow, openpyxl, pandas, PyMuPDF
