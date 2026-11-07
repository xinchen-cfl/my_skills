---
name: claude-clean-environment-mobile
description: 在安卓 Clash Meta 或 Mihomo 客户端中为 Claude 导入静态 Clash 配置，配置规则分流、TUN、Fake-IP、DNS 和直接 VPS 或链式出口。
---

# Claude 安卓端干净环境

适用于支持完整 Clash 配置文件的安卓客户端。安卓端优先导入静态 YAML，不要把节点和完整规则拆到“覆写”页面。

## 导入静态配置

静态配置应包含 `proxies`、`proxy-groups`、`rules`、TUN 和 DNS。把 YAML 放进手机文件管理器后，在客户端的“配置/文件 -> 导入”中选择它，并关闭该 profile 的自动更新。

导入后确认代理列表同时出现最终出口和代理组。不要只打开编辑器后保存就认为已切换；要返回配置列表并使用这份文件启动 VPN。

## 直接 VPS 出口

如果订阅中的美国 VPS 节点本身可以直接出站，配置只保留一个代理节点，不写 `dialer-proxy`：

```yaml
proxies:
  - name: 美国 VPS 直连
    type: vless
    # 其余节点字段使用服务商提供的值
    udp: true

proxy-groups:
  - name: 🔰国外流量
    type: select
    proxies: [美国 VPS 直连, ❌不代理]
  - name: 🤖AI服务
    type: select
    proxies: [🔰国外流量, 美国 VPS 直连]
  - name: ⚓️其他流量
    type: select
    proxies: [🔰国外流量, ❌不代理]
  - name: ❌不代理
    type: select
    proxies: [DIRECT]
```

## SOCKS5 链式出口

只有需要固定 SOCKS5 出口时才保留链式节点：

```yaml
  - name: 固定 SOCKS5 出口
    type: socks5
    server: EXIT_HOST
    port: EXIT_PORT
    username: EXIT_USERNAME
    password: EXIT_PASSWORD
    dialer-proxy: 中转节点
    udp: true
```

直接 VPS 和 SOCKS5 链式是两种独立配置，不要同时把 SOCKS5 设为默认出口。直接 VPS 的最终公网 IP 会是 VPS IP，链式配置的最终公网 IP 才是 SOCKS5 出口 IP。

## DNS、TUN 和规则

```yaml
mode: rule
ipv6: false
tun:
  enable: true
  auto-route: true
  auto-detect-interface: true
  dns-hijack: [any:53]
dns:
  enable: true
  enhanced-mode: fake-ip
  respect-rules: true
  proxy-server-nameserver:
    - 223.5.5.5
    - 119.29.29.29
```

当 `respect-rules: true` 时，`proxy-server-nameserver` 不能为空，否则客户端会报错。它只负责解析代理节点域名，不等于目标网站通过这些 DNS 直连。

把 BrowserLeaks 和 Claude/AI 域名规则放在 `GEOSITE,CN`、`GEOIP,CN` 和 `MATCH` 之前：

```yaml
rules:
  - DOMAIN-SUFFIX,browserleaks.com,🔰国外流量
  # Claude/AI 域名规则
  # 继续保留订阅的国内规则和其他规则
```

## 安卓系统选项

- 自动路由系统流量：开启；
- DNS 劫持：开启；
- 允许应用绕过 VPN：关闭；
- IPv6：上游不支持时关闭；
- TUN 开启后，系统 HTTP 代理不是必须，避免重复代理；
- 需要访问局域网设备时保留“绕过私有网络”，否则可关闭以严格接管流量。

模式选择规则模式；“不修改”也可以，只要 YAML 中已经是 `mode: rule`。不要选全局模式来替代分流。

## 验证

1. 启动 VPN 后确认代理组选择了正确的最终出口。
2. BrowserLeaks 的 Public IP 和 WebRTC Public IP 应一致并显示出口 IP。
3. IPv6 Leak 应无公网地址；DNS 检查不应出现本地运营商 DNS。
4. `172.16.0.0/12`、`10.0.0.0/8`、`192.168.0.0/16` 出现在 Local IP 是 TUN/局域网私有地址，不是公网泄露。
5. `udp: true` 只是允许尝试 UDP；是否成功取决于 VPS、链式节点和目标服务的支持。

