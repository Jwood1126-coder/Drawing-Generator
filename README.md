# Drawing Generator V3.2

A Python desktop application that generates batch images by overlaying Excel data onto drawing templates (PDFs/images). Built with CustomTkinter for a modern UI.

## Features

- **Template-based field placement** — Load a PDF or image drawing, then visually place data fields by clicking on the canvas
- **Excel data binding** — Map Excel columns to placed fields for batch generation
- **Drawing Templates (.dgt)** — Save reusable field layouts that can be applied across projects
- **Saved Projects (.dgp)** — Save complete project state including file paths, field placements, export settings, and edited data
- **Template vs Custom fields** — Distinguish between fields from a drawing template and one-off custom placements
- **Batch generation** — Generate images for all rows or a specific range from your Excel data
- **Per-part editing** — Preview and edit individual part data before generating
- **Export settings** — Configure output format, quality, DPI, and naming conventions
- **File converter** — Built-in PDF-to-image and image format converter
- **Theme support** — Multiple color themes with a modern, dark-mode-first UI

## Tech Stack

- **Python 3.13+**
- **CustomTkinter** — Modern themed Tkinter widgets
- **Pillow (PIL)** — Image processing and generation
- **openpyxl** — Excel file reading
- **pdf2image / Poppler** — PDF to image conversion
- **PyInstaller** — Single-file `.exe` builds

## Project Structure

```
├── app.py                  # Main application (UI + logic)
├── widgets.py              # Custom widget library (ModernButton, ModernEntry, etc.)
├── themes.py               # Theme system with ThemeManager
├── gui.py                  # Legacy GUI module
├── app_icon.ico            # Application icon
├── Image_Generator V3.2.spec  # PyInstaller build spec
├── panels/
│   ├── template_fields.py      # Field placement panel (Columns/Placed/Properties tabs)
│   ├── template_editor_canvas.py  # Interactive canvas for field placement
│   └── export_settings.py      # Export configuration panel
├── modules/
│   ├── excel_reader.py     # Excel file parsing
│   ├── pdf_converter.py    # PDF to image conversion
│   ├── template_editor.py  # Template mapping and field template classes
│   ├── size_limits.py      # Image size constraints
│   └── utils.py            # Shared utilities
└── .gitignore
```

## Usage

### Running from source
```bash
pip install customtkinter pillow openpyxl pdf2image
python app.py
```

### Building the executable
```bash
pip install pyinstaller
pyinstaller --noconfirm "Image_Generator V3.2.spec"
# Output: dist/Image_Generator V3.2.exe
```

### Workflow
1. **Load files** — Select a drawing template (PDF/image), Excel data file, and output folder
2. **Select or create a project** — Use the PROJECT card to manage saved projects
3. **Apply a drawing template** (optional) — Pick a reusable field layout from the template library
4. **Place fields** — Select Excel columns and click on the drawing to position them
5. **Preview** — Step through parts to verify placement and edit values
6. **Generate** — Batch generate images for all parts or a selected range

## Data Storage

- **Projects (.dgp)** — Saved in `%APPDATA%/DrawingGenerator/projects/`
- **Templates (.dgt)** — Saved in a configurable shared folder (default: `%APPDATA%/DrawingGenerator/`)
- **Settings** — `%APPDATA%/DrawingGenerator/settings.json`

## License

Private repository.
