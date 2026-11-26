# my_skills

自建实战经验 Skill 集合。所有示例均已脱敏，不含真实 IP、订阅链接或凭据。

## Claude 干净出海环境

核心思路只有两步：

1. **先买一个干净的静态 IP 出口**（推荐美国静态住宅 SOCKS5，用日常机场订阅做前置中转，兼顾连通率与固定纯净 IP）。
2. **再做 VPN 规则分流策略**（保证 Claude / AI 流量稳定走该静态出口，国内流量直连，DNS 与 WebRTC 不泄露）。

### 目录索引

| Skill 目录 | 适用平台与客户端 | 核心做法 | 独立分流策略文件 |
|---|---|---|---|
| [claude-clean-environment-desktop](skills/claude-clean-environment-desktop/SKILL.md) | Windows / macOS / Linux（Clash Verge / Mihomo） | 机场订阅 + 独立覆写文件（防刷新覆盖） | [routing-strategy.md](skills/claude-clean-environment-desktop/references/routing-strategy.md) |
| [claude-clean-environment-mobile](skills/claude-clean-environment-mobile/SKILL.md) | Android（Clash Meta / Mihomo） | 导入单份完整静态 YAML（关闭自动更新） | [routing-strategy.md](skills/claude-clean-environment-mobile/references/routing-strategy.md) |
