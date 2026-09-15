from pathlib import Path


PROJECT_ROOT = Path(SPECPATH).resolve().parent
ENTRYPOINT = PROJECT_ROOT / "packaging" / "explorer_entry.py"
SCHEMA_ROOT = PROJECT_ROOT / "schemas"

if not ENTRYPOINT.is_file():
    raise FileNotFoundError(f"Explorer entry point does not exist: {ENTRYPOINT}")
if not SCHEMA_ROOT.is_dir():
    raise FileNotFoundError(f"Census schema directory does not exist: {SCHEMA_ROOT}")


a = Analysis(
    [str(ENTRYPOINT)],
    pathex=[str(PROJECT_ROOT / "src")],
    binaries=[],
    datas=[(str(SCHEMA_ROOT), "share/manafold-census/schemas")],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="manafold-census-explorer",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
COLLECT(
    exe,
    a.binaries,
    a.datas,
    a.zipfiles,
    a.zipped_data,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="manafold-census-explorer",
)
