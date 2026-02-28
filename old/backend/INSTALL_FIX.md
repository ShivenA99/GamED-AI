# Installation Fix for Rust/Pydantic Issues

If you encounter errors about Rust/Cargo when installing dependencies, try these solutions:

## Solution 1: Use Updated Requirements (Recommended)

The `requirements.txt` has been updated to use newer versions with pre-built wheels. Try:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

## Solution 2: Install Rust Properly

If Solution 1 doesn't work, install Rust properly:

1. Download and install Rust from: https://rustup.rs/
2. Restart your terminal/PowerShell
3. Verify installation: `cargo --version`
4. Try installing again: `pip install -r requirements.txt`

## Solution 3: Use Alternative PDF Library

If PyPDF2 causes issues, you can use pypdf instead:

```bash
pip install fastapi uvicorn[standard] python-multipart pydantic openai anthropic python-docx pypdf aiofiles python-jose[cryptography] python-dotenv
```

## Solution 4: Use Python 3.11 or 3.12

Python 3.14 is very new and may not have pre-built wheels for all packages. Consider using Python 3.11 or 3.12:

```bash
# Create new venv with Python 3.11/3.12
python3.11 -m venv venv
# or
python3.12 -m venv venv
```

Then install dependencies normally.

## Quick Fix Command

Try this sequence:

```powershell
# Upgrade pip first
python -m pip install --upgrade pip

# Clear pip cache
pip cache purge

# Install with no cache
pip install --no-cache-dir -r requirements.txt
```

