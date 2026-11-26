# VPN 分流策略独立规范

适用于 Clash Verge / Mihomo（电脑端）及 Clash Meta / Mihomo（安卓端）。核心目标是把**“最终静态出口”**与**“前置机场中转”**拆成两层，做到切换机场线路不改变最终公网 IP，同时确保 AI 流量不漏、国内流量不绕路。

---

## 1. 两层链式转发模型

- **日常稳态（走干净静态出口）**：`🔰国外流量` 选 `美国 NTT 链式出口`
  ```text
  设备 -> ↗️上游直连（任选机场节点） -> 美国 NTT 链式出口（固定静态 IP） -> 目标网站
  ```
- **临时切换（走普通机场出口）**：`🔰国外流量` 选 `↗️上游直连`
  ```text
  设备 -> ↗️上游直连（选中的机场节点） -> 目标网站
  ```

只要 `美国 NTT 链式出口` 节点的 `dialer-proxy` 指向 `↗️上游直连`，平时某个机场节点卡顿时，在 `↗️上游直连` 里随便换节点，最终对外暴露的公网出口 IP 始终保持不变。

---

## 2. 标准代理组配置（`proxy-groups`）

核心链路只维护 `🔰国外流量` 和 `↗️上游直连` 两个组；其余分类组（`🤖AI服务`、`⚓️其他流量`、`🍎苹果服务`、`❌不代理`）统一指向 `🔰国外流量` 或 `DIRECT`，不要再单独复制一套静态出口前置组，也不要把前置死绑在某一个单节点上：

```yaml
proxy-groups:
  - name: 🔰国外流量
    type: select
    proxies:
      - 美国 NTT 链式出口
      - ↗️上游直连

  - name: ↗️上游直连
    type: select
    use:
      - 机场订阅
    proxies:
      - 静态备用节点

  - name: 🤖AI服务
    type: select
    proxies:
      - 🔰国外流量

  - name: ⚓️其他流量
    type: select
    proxies:
      - 🔰国外流量
      - ❌不代理

  - name: 🍎苹果服务
    type: select
    proxies:
      - ❌不代理
      - 🔰国外流量

  - name: ❌不代理
    type: select
    proxies:
      - DIRECT
```

*(注：这里把 `美国 NTT 链式出口` 放在 `🔰国外流量` 第一顺位，导入后默认即生效为干净静态出口。)*

---

## 3. 分流规则优先级（从上到下按顺序匹配）

Clash / Mihomo 规则自上而下命中即停，靠后的规则无法覆盖前置规则，严格按以下 6 层顺序排列：

1. **IPv6 阻断/处理**：在上游不支持 IPv6 时优先拦截或关闭 IPv6，防绕过代理直连泄露。
2. **AI 与环境检测域名（最高业务优先级）**：将 Claude（`anthropic.com`、`claude.ai`）、OpenAI、Google AI 以及验 IP 站点（`browserleaks.com`）排在所有国内规则之前，固定指向 `🤖AI服务` 或 `🔰国外流量`。
3. **局域网与系统连通性探测**：内网网段（LAN）及明确需要直连的本地服务指向 `DIRECT`。
4. **国内流量直连**：Steam 国内下载 CDN、常用国内域名，以及 `GEOSITE,cn`、`GEOIP,CN,no-resolve` 指向 `❌不代理`（若个别国内域名被误判走海外，在此层之前补一条具体的 `DOMAIN-SUFFIX,xxx.com,❌不代理`）。
5. **通用海外规则**：`GEOSITE,geolocation-!cn` 等常规海外流量指向 `🔰国外流量`。
6. **末尾兜底规则**：最后一行固定为 `MATCH,⚓️其他流量`（默认跟走国外流量，特殊情况下可在界面一键切回不代理；严禁用客户端“全局模式”代替规则模式）。

### 最小规则骨架示例

```yaml
rules:
  # 1. 检测站与核心 AI 服务（必须在国内规则之前）
  - DOMAIN-SUFFIX,browserleaks.com,🔰国外流量
  - DOMAIN-SUFFIX,claude.ai,🤖AI服务
  - DOMAIN-SUFFIX,anthropic.com,🤖AI服务
  - DOMAIN-SUFFIX,openai.com,🤖AI服务
  - DOMAIN-SUFFIX,chatgpt.com,🤖AI服务
  - DOMAIN-SUFFIX,gemini.google.com,🤖AI服务

  # 2. 局域网直连
  - GEOIP,PRIVATE,DIRECT,no-resolve

  # 3. 国内服务直连（加 no-resolve 防止本地 DNS 抢答泄露）
  - GEOSITE,cn,❌不代理
  - GEOIP,CN,❌不代理,no-resolve

  # 4. 其余海外与最终兜底
  - GEOSITE,geolocation-!cn,🔰国外流量
  - MATCH,⚓️其他流量
```

---

## 4. 订阅更新与安全红线

1. **防刷新覆盖**：机场节点通过 `proxy-providers` / `use` 自动拉取更新；`美国 NTT 链式出口`、`proxy-groups` 和自定义 `rules` 必须写在电脑端独立覆写文件或移动端关闭了自动更新的静态主配置里。
2. **移动端兼容**：在 `↗️上游直连` 的 `proxies` 下保留至少 1 个静态备用节点，防止部分客户端在 Provider 未展开时报错。
3. **信息脱敏**：严禁将真实机场订阅 URL、SOCKS5 账号密码、UUID 或真实公网 IP 写入仓库文件与示例。
