# 分流策略参考

这套策略适用于 Clash Verge/Mihomo 和支持完整 Clash YAML 的移动端客户端。它把“最终出口选择”和“NTT 前置节点选择”分开，同时保留分类代理组供查看和分流。

## 链路模型

```text
选择 ↗️上游直连
设备 -> 选中的机场节点 -> 目标网站

选择 美国 NTT 链式出口
设备 -> ↗️上游直连中选中的机场节点 -> NTT SOCKS5 -> 目标网站
```

NTT 节点的 `dialer-proxy` 必须指向 `↗️上游直连`，因此更换上游节点只改变到 NTT 的中继路径，最终公网出口仍然是 NTT。

## 代理组

保留以下组，避免客户端界面只显示一个难以管理的入口：

```yaml
proxy-groups:
  - name: 🔰国外流量
    type: select
    proxies:
      - ↗️上游直连
      - 美国 NTT 链式出口

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

`🔰国外流量` 和 `↗️上游直连` 是两个核心选择层；其他组保留在界面中，用于分类规则和必要时的人工切换。AI 组默认跟随 `🔰国外流量`，因此不需要额外复制一套 NTT 逻辑。

## 规则优先级

规则按以下顺序组织：

1. 禁止或处理 IPv6（仅在确实关闭 IPv6 时使用对应规则）。
2. BrowserLeaks、Claude、OpenAI、Google AI 等需要稳定国外出口的域名，放在国内规则前，指向 `🔰国外流量` 或 `🤖AI服务`。
3. 局域网、系统连通性检查和明确允许直连的服务，指向 `DIRECT`。
4. Steam 国内下载、国内服务和 `GEOSITE,CN`/`GEOIP,CN` 规则，指向 `❌不代理` 或 `DIRECT`。
5. 其他国外规则指向 `🔰国外流量`。
6. 最后一条使用 `MATCH,⚓️其他流量`，保留人工选择“国外流量/不代理”的能力。

最小关键片段：

```yaml
rules:
  - DOMAIN-SUFFIX,browserleaks.com,🔰国外流量
  # Claude/OpenAI/Google AI 规则放在 GEOSITE,CN、GEOIP,CN 和 MATCH 之前
  - GEOSITE,cn,❌不代理
  - GEOIP,CN,❌不代理,no-resolve
  - MATCH,⚓️其他流量
```

如果某个国内域名被误判为国外，添加更具体的 `DOMAIN` 或 `DOMAIN-SUFFIX` 直连规则，并放在通用规则之前。不要用全局模式替代规则模式；全局模式会让国内流量也消耗国外出口。

## 自动更新不变量

- 机场节点由 `proxy-providers`/`use` 自动更新。
- NTT 节点和代理组放在主配置或覆写中，不能只写在会被刷新覆盖的订阅内容里。
- Provider 无法展开时，在 `proxies` 中保留静态备用节点，确保移动端仍能显示节点。
- 不要把真实订阅 URL、账号、密码、UUID 或公网 IP 写入 skill、脚本和示例。
