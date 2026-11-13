# -*- coding: utf-8 -*-
"""
install_agent_rules.py — 把 repo 裡的 agent 守則裝到本機 Claude Code（~/.claude）。

用法:  python tools/install_agent_rules.py

  agent/ai-agent-guide.md                  → ~/.claude/agent-core.md（由 ~/.claude/CLAUDE.md 以 @ 引用，每個 session 都讀）
  agent/skills/agent-config-writing/       → ~/.claude/skills/agent-config-writing/（需要時才載入的 skill）
  agent/agents/*.md                        → ~/.claude/agents/（子 agent，例如 reviewer）
  agent/commands/*.md                      → ~/.claude/commands/（使用者指令，例如 /review、/handoff）

守則與 skill 也顯示在網站的筆記分頁上（網站版與 agent 讀的是同一份）。
可重複執行：更新後再跑一次就會覆蓋成新版；~/.claude/CLAUDE.md 的其他內容不會被動到。
"""
import shutil
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
AGENT = REPO / "agent"
HOME = Path.home() / ".claude"
IMPORT_LINE = "@~/.claude/agent-core.md"

HOME.mkdir(exist_ok=True)
shutil.copyfile(AGENT / "ai-agent-guide.md", HOME / "agent-core.md")
print(f"工作守則 -> {HOME / 'agent-core.md'}")

skill_dst = HOME / "skills" / "agent-config-writing"
shutil.copytree(AGENT / "skills" / "agent-config-writing", skill_dst, dirs_exist_ok=True)
print(f"skill -> {skill_dst}")

for sub in ("agents", "commands"):
    dst = HOME / sub
    dst.mkdir(exist_ok=True)
    for f in sorted((AGENT / sub).glob("*.md")):
        shutil.copyfile(f, dst / f.name)
        print(f"{sub[:-1]} -> {dst / f.name}")

claude_md = HOME / "CLAUDE.md"
text = claude_md.read_text(encoding="utf-8") if claude_md.exists() else ""
if IMPORT_LINE not in text:
    block = ("# 全域工作守則（來源：a638138/economist repo 的 agent/ai-agent-guide.md，"
             "更新後執行 tools/install_agent_rules.py）\n" + IMPORT_LINE + "\n")
    claude_md.write_text((text.rstrip() + "\n\n" if text.strip() else "") + block, encoding="utf-8")
    print(f"已在 {claude_md} 加入引用")
else:
    print(f"{claude_md} 已有引用，未變更")
