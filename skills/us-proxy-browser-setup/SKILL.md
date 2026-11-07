---
name: us-proxy-browser-setup
description: 当需要在安装了 Clash 或 Mihomo 的电脑或安卓设备上，用已有分流订阅、中转节点和固定 HTTP/SOCKS5 出口配置稳定链路时使用；适用于浏览器和应用流量验证，不保证隐藏设备指纹或改变账号风控结果。
---

# Clash 链式出口最小配置

如果订阅已经提供了分流规则和中转节点，通常不需要重新搭建完整 Mihomo 配置。只需要：

```text
已有订阅分流
  -> 中转节点
  -> 固定 HTTP/SOCKS5 出口
  -> 目标网站
```

不要把出口账号、密码、订阅 URL 或真实 IP 写入 Skill、截图或日志。

## 1. 确认中转订阅

先确认订阅单独使用时可以联网，并确认中转节点的名称，例如：

```text
美国632 中继
```

保留订阅原有的国内/国外分流规则。Clash 规则按从上到下匹配；如果某个站点被 `GEOSITE,cn` 或 `GEOIP,CN` 提前判定为直连，需要增加更靠前的站点规则覆盖它。

## 2. 在“覆写基本/配置文本”追加出口节点

在 Clash Verge 的覆写配置中追加节点。出口节点的 `dialer-proxy` 指向中转节点，名称必须完全一致：

```yaml
prepend: []
append:
  - name: 固定出口
    type: socks5                 # 按服务商说明，也可能是 http
    server: EXIT_HOST
    port: EXIT_PORT
    username: EXIT_USERNAME
    password: EXIT_PASSWORD
    dialer-proxy: 中转节点
    udp: true
delete: []
```

如果服务商只提供 HTTP 代理，将 `type` 改为 `http`，不要凭猜测把 HTTP 写成 SOCKS5。

在当前订阅中，代理组会自动收录 `append` 新增节点，所以追加这一段后节点会出现在 `🔰国外流量`。换一个订阅服务商时必须检查：

```text
代理组是否包含 固定出口
代理组当前是否选中 固定出口
```

如果没有自动收录，就在覆写配置中把节点名称加入目标 `proxy-groups`，或在 Clash Verge 的代理组界面手动选择。

`dialer-proxy` 只负责让出口端点通过中转连接；它不改变分流规则，也不保证出口服务商支持链式代理。先确认中转可用，再测试完整链路。

## 3. 固定分流策略

保留订阅原有的国内规则，把需要稳定出口的网站规则放在 `GEOSITE,CN`、`GEOIP,CN` 和 `MATCH` 之前。推荐的代理组关系如下，名称可按实际订阅调整：

```yaml
proxy-groups:
  - name: 🔰国外流量
    type: select
    proxies: [固定出口, 中转节点, ❌不代理]
  - name: 🤖AI服务
    type: select
    proxies: [🔰国外流量, 固定出口, 中转节点]
  - name: ⚓️其他流量
    type: select
    proxies: [🔰国外流量, ❌不代理]
  - name: ❌不代理
    type: select
    proxies: [DIRECT]

rules:
  - DOMAIN-SUFFIX,browserleaks.com,🔰国外流量
  # AI 服务规则放在国内规则之前；其余订阅规则继续保留
```

要让未被明确判定为国内的流量也走国外，选择 `⚓️其他流量 -> 🔰国外流量`。如果只想按规则分流，则保留订阅原来的其他流量选择。不要把 `全局模式` 当作分流策略，它会把国内流量也送入出口并增加用量。

## 4. 安卓静态配置

安卓客户端支持完整 Clash 配置时，优先导入静态 YAML，不要把节点和规则拆到“覆写”页面。静态文件应包含 `proxies`、`proxy-groups`、`rules`、TUN 和 DNS；关闭自动更新，避免订阅刷新覆盖链式出口。

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

`respect-rules: true` 时，`proxy-server-nameserver` 不能留空；它负责解析中转节点域名，否则客户端会报错。它是代理端点的引导解析，不代表目标网站会直连这些 DNS。

安卓客户端建议：

- 自动路由系统流量：开；
- DNS 劫持：开；
- 允许应用绕过 VPN：关；
- IPv6：上游不支持时关；
- TUN 已开启时，系统 HTTP 代理不是必须，避免重复套代理；
- 需要局域网设备时保留“绕过私有网络”，否则可关闭以严格接管流量。

## 5. 验证链路

BrowserLeaks 中 `Public IP` 和 WebRTC 的 `Public IP` 应显示固定出口。`172.16.0.0/12`、`10.0.0.0/8`、`192.168.0.0/16` 等地址出现在 `Local IP` 栏是 TUN/局域网私有地址，不是公网泄露；只有 WebRTC 公网地址出现本地运营商公网 IP 才算泄露。另行检查 IPv6 和 DNS，浏览器通过不等于所有应用都没有自己的绕过路径。

## 6. 选择 UDP 策略

### 需要 UDP

出口和中转节点都设置：

```yaml
udp: true
```

并确认服务商实际支持 UDP。WebRTC、部分实时通信、游戏和 QUIC 可能需要 UDP。

### 不需要或不确定 UDP

开启客户端的“禁止非代理 UDP”，对应某些客户端中的：

```yaml
disable_non_proxied_udp: true
```

不支持代理的 UDP 会失败，而不是自动直连；代价是 WebRTC 或其他 UDP 应用可能不可用。

允许 UDP 也不代表一定走出口。`DIRECT`、`GEOSITE,CN`、`GEOIP,CN`、局域网规则和应用自己的 VPN/网络扩展仍可能改变路径。

## 7. 持久化规则

不要直接改订阅刷新生成的主 YAML。使用以下任一位置：

1. 覆写基本或配置文本：适合追加节点、修改基础字段；
2. 合并配置：适合保存固定节点和代理组；
3. 扩展脚本：适合订阅加载后强制插入站点规则。

例如，强制 BrowserLeaks 排在 `GEOSITE,cn` 之前：

```javascript
function main(config) {
  const rule = "DOMAIN-SUFFIX,browserleaks.com,🔰国外流量";
  config.rules = Array.isArray(config.rules) ? config.rules : [];
  config.rules = config.rules.filter(item => {
    const text = Array.isArray(item) ? item.join(",") : String(item);
    return !/^DOMAIN-SUFFIX,browserleaks\.com,/i.test(text);
  });
  config.rules.unshift(rule);
  return config;
}
```

## 8. 最小验证

1. 开启 TUN（要让桌面应用也被接管）；只测试浏览器时可使用本地 HTTP/SOCKS5 代理。
2. 在 Clash Verge 中选择目标代理组和固定出口。
3. 检查 BrowserLeaks 的 HTTP、IPv6、DNS、WebRTC；HTTP 和 WebRTC 公网 IP 应符合预期。
4. 在“连接”页面检查真实链路，确认目标请求包含中转节点和固定出口。
5. 测试桌面应用时，按应用域名查看连接记录；浏览器测试通过不等于所有应用都没有自己的绕过路径。

## 9. 迁移到新电脑

在新电脑安装 Clash/Mihomo，导入同一中转订阅，在覆写配置中追加同类出口节点，确认代理组收录并选中它，按“最小验证”重新测试。不要复制浏览器 Cookie、密码、Local Storage 或完整浏览器用户目录。

## 结论

- 订阅已有分流和中转：通常只需覆写 `append` 出口节点；
- `dialer-proxy` 名称必须精确匹配中转节点；
- `udp: true` 是允许尝试 UDP，不是对服务商能力的保证；
- 禁止非代理 UDP 时，不支持代理的 UDP 会失败，不会自动直连；
- 出口显示美国不等于住宅 IP，仍需查看 ISP、ASN、Usage Type 和 IP 信誉。
