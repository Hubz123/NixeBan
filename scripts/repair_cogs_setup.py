#!/usr/bin/env python3
import ast, re
from pathlib import Path
root = Path(__file__).resolve().parents[1]
cogs = root/'nixe'/'cogs'
fixed=0; skipped=0
for p in sorted(cogs.glob("*.py")):
    src = p.read_text(encoding="utf-8", errors="ignore")
    try:
        tree = ast.parse(src)
    except Exception:
        continue
    has_setup=False
    for node in ast.walk(tree):
        if isinstance(node,(ast.FunctionDef, ast.AsyncFunctionDef)) and node.name=="setup":
            if node.args.args and node.args.args[0].arg=="bot": has_setup=True
    if has_setup: 
        skipped+=1; 
        continue
    # Heuristic: find exactly one Cog class
    cog_classes=[m.group(1) for m in re.finditer(r"class\s+(\w+)\s*\(.*commands\.Cog\)", src)]
    if len(cog_classes)==1:
        cname=cog_classes[0]
        src += f"\n\nasync def setup(bot):\n    await bot.add_cog({cname}(bot))\n"
        p.write_text(src, encoding="utf-8"); fixed+=1
    else:
        skipped+=1
print(f"[OK] setup injected: {fixed}, skipped: {skipped}")
