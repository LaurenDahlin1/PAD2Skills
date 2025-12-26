# Notes 
Many of these notes will be added to Readme.md

## Set up

### How I set up the environment 
1. Install uv. If you have homebrew you can do the following in your terminal. 
`brew install uv`
2. `cd` into `PAD2Skills` in terminal or open a new terminal in VS Code  
3. This project is built with python 3.11. In termainal:
`uv python pin 3.11`
4. Initialize uv
`uv init --bare`
5. Add version to .toml fie
`requires-python = "==3.11.*"`
6. Create a fresh venv and sync
`uv venv --python 3.11`
`uv sync`
7. Add packages
`uv add --dev ipykernel pytest ruff`
`uv add pandas dash plotly "docling" "torch<2.3" "numpy<2.0.0"`
`uv sync`