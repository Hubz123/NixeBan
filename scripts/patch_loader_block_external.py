
#!/usr/bin/env python3
import re, pathlib
loader = pathlib.Path("nixe/cogs_loader.py")
src = loader.read_text(encoding="utf-8", errors="ignore")
orig = src
if "apply_module_filter" not in src:
    src = re.sub(r"(^\s*import\s+logging.*?$)", r"\1\nfrom nixe.cogs.cogs_loader_patch import apply_module_filter", src, flags=re.M)
if "apply_module_filter(mods)" not in src:
    src = re.sub(r"mods\s*=\s*(\[[^\]]*\]|list\([^\)]*\)|[^\n]+)", r"mods = apply_module_filter(\1)", src, count=1)
    if "apply_module_filter(mods)" not in src:
        src = re.sub(r"(for\s+\w+\s+in\s+mods\s*:)", "mods = apply_module_filter(mods)\n\1", src, count=1)
if src != orig:
    loader.write_text(src, encoding="utf-8")
    print("[ok] cogs_loader.py patched to filter external modules")
else:
    print("[note] patcher did not change cogs_loader.py (maybe already patched)")
