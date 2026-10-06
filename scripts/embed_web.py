"""Embed the dependency-free web UI in firmware; no build-time npm dependencies."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
source=(root/'firmware/web/index.html').read_text(encoding='utf-8')
assert ')STWEB"' not in source
(root/'firmware/simple_touch/web_ui.h').write_text('#pragma once\nconst char WEB_UI[] PROGMEM = R"STWEB('+source+')STWEB";\n',encoding='utf-8',newline='\n')
