---
name: claude-clean-environment-desktop
description: 在电脑上使用 Clash Verge 或 Mihomo 为 Claude 配置规则分流、直接 VPS 出口或 SOCKS5 链式出口，并验证公网 IP、DNS、IPv6 与 WebRTC。
---

# Claude 电脑端干净环境

适用于 Windows、macOS 和 Linux 的 Clash Verge/Mihomo。电脑端优先使用“订阅 + 独立覆写文件”，不要直接编辑订阅生成的主 YAML。

## 选择出口模式

### VPS 直接出口

当订阅节点本身是可直接出站的美国 VPS 时，让它直接成为最终出口：

```text
订阅中的美国 VPS 节点
        -> 目标网站
```

不要添加 `dialer-proxy`，也不要再叠加 NTT SOCKS5。订阅节点名称通常会带流量和到期时间，使用脚本重命名为稳定名称，例如 `美国 VPS 直连`，再在代理组中引用稳定名称。

```javascript
function main(config) {
  const prefix = "VPS_NODE_PREFIX";
  const stableName = "美国 VPS 直连";
  const proxies = Array.isArray(config.proxies) ? config.proxies : [];
  const node = proxies.find(item =>
    item && typeof item.name === "string" && item.name.startsWith(prefix)
  );
  if (!node) return config;
  node.name = stableName;
  config.proxies = proxies.filter(item => item !== node && item.name !== stableName);
  config.proxies.push(node);
  return config;
}
```

### 固定 SOCKS5 链式出口

仅当需要固定 SOCKS5 出口时使用链式模式：

```text
订阅中转节点
        -> SOCKS5 出口
        -> 目标网站
```

```yaml
append:
  - name: 固定 SOCKS5 出口
    type: socks5
    server: EXIT_HOST
    port: EXIT_PORT
    username: EXIT_USERNAME
    password: EXIT_PASSWORD
    dialer-proxy: 中转节点
    udp: true
```

`dialer-proxy` 名称必须与中转节点完全一致。出口服务商只提供 HTTP 时，将 `type` 写成 `http`，不要猜测协议。

### 多节点链式代理组

需要“任意机场节点作为前置，但最终始终从固定 NTT 出口”时，使用两层核心结构：

```text
↗️上游直连（可选任意机场节点）
        ↓ 作为 dialer-proxy
美国 NTT 链式出口（固定最终出口）
        ↓
目标网站
```

```yaml
proxies:
  - name: 美国 NTT 链式出口
    type: socks5
    server: EXIT_HOST
    port: EXIT_PORT
    username: EXIT_USERNAME
    password: EXIT_PASSWORD
    dialer-proxy: ↗️上游直连
    udp: true

proxy-groups:
  - name: 🔰国外流量
    type: select
    proxies:
      - ↗️上游直连
      - 美国 NTT 链式出口
  - name: ↗️上游直连
    type: select
    use: [机场订阅]
    proxies: [静态备用节点]
```

`↗️上游直连` 同时承担两件事：直接访问目标网站，以及作为 NTT 的上一跳。选择 `🔰国外流量 -> 美国 NTT 链式出口` 时，切换上游节点只会改变到 NTT 的路径，最终公网出口仍是 NTT；选择 `🔰国外流量 -> ↗️上游直连` 时，最终出口则是选中的机场节点。

可以继续保留 `🤖AI服务`、`⚓️其他流量`、`🍎苹果服务`、`❌不代理` 等分类组供查看和规则分流，但不要再为 NTT 单独创建一个固定 632 的前置组。分类组应指向 `🔰国外流量` 或 `↗️上游直连`，核心链路只维护上述两个组。

使用 `proxy-providers.use` 获取自动更新节点，并在 `proxies` 中保留静态备用节点，兼容无法展开 Provider 的客户端。Provider 刷新只更新机场节点；`美国 NTT 链式出口` 和代理组必须保持在主配置/覆写中，避免被订阅覆盖。

## 覆写文件分工

建议把电脑 profile 拆成独立覆写文件：

- `merge`：DNS、Fake-IP 和基础设置；
- `script`：识别动态订阅节点并重命名；
- `rules`：完整分流规则；
- `proxies`：静态追加的 SOCKS5/HTTP 出口；
- `groups`：代理组及默认选择。

订阅刷新只更新基础节点；独立覆写文件会继续应用。不要把真实账号、密码、订阅 URL 或公网 IP 写进 skill、脚本示例或截图。

## 分流策略

完整的已验证组结构、规则顺序和自动更新不变量见 [references/routing-strategy.md](references/routing-strategy.md)。

将固定出口或直连 VPS 放在国外流量组的第一选择，并把特殊站点规则放在国内规则之前：

```yaml
proxy-groups:
  - name: 🔰国外流量
    type: select
    proxies: [美国 VPS 直连, 固定 SOCKS5 出口, ❌不代理]
  - name: 🤖AI服务
    type: select
    proxies: [🔰国外流量, 美国 VPS 直连, 固定 SOCKS5 出口]
  - name: ⚓️其他流量
    type: select
    proxies: [🔰国外流量, ❌不代理]
  - name: ❌不代理
    type: select
    proxies: [DIRECT]

rules:
  - DOMAIN-SUFFIX,browserleaks.com,🔰国外流量
  # Claude/AI 域名规则应放在 GEOSITE,CN、GEOIP,CN 和 MATCH 之前
```

如果希望所有未明确判定为国内的流量走国外，选择 `⚓️其他流量 -> 🔰国外流量`。不要使用全局模式代替分流；全局模式会增加国内流量的出口用量。

## 运行与验证

1. 规则模式下开启 TUN，才能接管桌面应用；只代理浏览器时可使用本地 HTTP/SOCKS5 端口。
2. 选择目标代理组和最终出口，确认连接日志包含预期节点。
3. 在 BrowserLeaks 检查 HTTP、IPv6、DNS、WebRTC；HTTP 和 WebRTC 的公网 IP 应一致并符合出口预期。
4. `172.16.0.0/12`、`10.0.0.0/8`、`192.168.0.0/16` 出现在 Local IP 是虚拟网卡/局域网地址，不是公网泄露。
5. 浏览器测试通过不等于每个桌面应用都经过同一路径；按应用域名查看连接记录。

## UDP

`udp: true` 只表示允许尝试 UDP，不保证中转、出口或目标服务真正支持。WebRTC、QUIC、实时通信和游戏可能需要 UDP；不确定时可开启“禁止非代理 UDP”，代价是这些应用可能不可用。

