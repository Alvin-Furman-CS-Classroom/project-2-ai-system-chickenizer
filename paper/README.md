# Chickenizer term paper (LaTeX)

This directory holds the CSC 343 final paper source, figures, and a minimal `grfext` stub for incomplete TinyTeX installs.

## Build

From this directory:

```bash
pdflatex -interaction=nonstopmode main.tex
bibtex main
pdflatex -interaction=nonstopmode main.tex
pdflatex -interaction=nonstopmode main.tex
```

Or with `latexmk` (if installed):

```bash
latexmk -pdf -interaction=nonstopmode main.tex
```

## View the PDF in Cursor

Cursor is VS Code–compatible, so you can treat LaTeX like any other project:

1. **Terminal (simplest)**  
   Run the build commands above, then open `paper/main.pdf`:
   - Click `main.pdf` in the file explorer, or  
   - From the repo root: `open paper/main.pdf` (macOS).

2. **LaTeX Workshop extension (build + preview inside the editor)**  
   - Open Extensions (`Cmd+Shift+X`), search **LaTeX Workshop** (by James Yu), install.  
   - Open `paper/main.tex`, use the **TeX** sidebar or `Cmd+Alt+B` (default recipe: `latexmk` or `pdflatex`).  
   - PDF preview opens in a tab; SyncTeX jumps between source and PDF if enabled in settings.

3. **If PDF preview is blank**  
   Ensure `latexmk` or `pdflatex` is on your `PATH` (TinyTeX/MacTeX). Build once from the terminal to see errors.

## Figures

- `figures/architecture.png` — regenerate with `python3 scripts/gen_architecture_figure.py` (requires matplotlib).
- `figures/ql_pairwise_heatmap.png` — copied from the repo `graphics/` tree for a self-contained paper folder; re-copy after regenerating that asset if needed.

## `grfext.sty`

Some minimal TeX distributions omit the CTAN `grfext` package, which `epstopdf-base` pulls in when graphics drivers load options. A tiny local `grfext.sty` stub ships here so `pdflatex` succeeds; replace it with a full install (`tlmgr install grfext`) if you prefer not to rely on stubs.

## Word count

Course rules exclude the abstract, references, captions, and appendices from the main-body target (2,200–2,500 words).

- **If `texcount` is installed:**  
  `texcount -1 -sum -inc sections/introduction.tex sections/architecture.tex ...` (all `sections/*.tex` except `abstract.tex`).

- **Quick local estimate (no texcount):**  
  `python3 scripts/wordcount_body.py`  
  This strips LaTeX roughly and drops `\caption{...}` text so it is closer to “body without captions.” Prefer `texcount` or Overleaf for the final number your instructor expects.
