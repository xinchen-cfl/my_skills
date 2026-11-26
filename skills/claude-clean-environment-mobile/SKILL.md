---
name: claude-clean-environment-mobile
description: 在安卓端（Clash Meta 或 Mihomo）搭建干净稳定的 Claude 出海环境：导入包含静态 IP 链式出口、TUN、Fake-IP DNS 与分流规则的完整静态 YAML，并完成公网 IP、DNS、IPv6 与 WebRTC 防漏验证。
---

# Claude 安卓端干净环境（Clash Meta / Mihomo）

搭建不触发风控的 Claude 环境，核心只做两件事：**1. 准备一个干净的静态 IP 出口；2. 配置 VPN 分流策略稳定接管流量**。

安卓端与电脑端不同：**优先整理好一份完整的静态 YAML 直接导入**（内含节点、代理组、TUN、DNS 和分流规则），不要把节点和规则拆到客户端的“覆写”页面，导入后关闭该配置的自动更新。

---

## 标准实操步骤

### 1. 准备干净的静态 IP 出口
- **首选方案（静态住宅 SOCKS5/HTTP 链式出口）**：购买干净独享的美国静态住宅代理（例如 NTT 静态住宅 IP），通过日常机场节点做前置中转（`dialer-proxy`）连接。
- **备选方案（自有美国原生 VPS 直出）**：若自有可直接出站且 IP 干净的美国 VPS，无需叠加链式代理，见文末「附：自有美国 VPS 直接出口」。

### 2. 编写静态 YAML 核心节点与 TUN / DNS 配置
1. **写入静态链式出口节点**：在 YAML 的 `proxies` 中添加购买的静态出口，将 `dialer-proxy` 指向前置机场组 `↗️上游直连`：
   ```text
   手机 -> ↗️上游直连（任意可用机场节点） -> 美国 NTT 链式出口（固定静态 IP） -> Claude / 目标网站
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
   ```
   *(注：若服务商只给 HTTP 代理则填 `type: http`；不要把真实凭据或公网 IP 写入公开仓库与示例。)*

2. **写入安卓端 TUN 与 Fake-IP DNS 基础块**：
   ```yaml
   mode: rule
   ipv6: false
   tun:
     enable: true
     auto-route: true
     auto-detect-interface: true
     dns-hijack:
       - any:53
   dns:
     enable: true
     enhanced-mode: fake-ip
     respect-rules: true
     proxy-server-nameserver:
       - 223.5.5.5
       - 119.29.29.29
   ```
   - **关键避坑**：开启 `respect-rules: true` 时，`proxy-server-nameserver` **必填不能为空**，否则客户端启动会直接报错；它只负责解析前置机场节点自身的服务器域名，不会让目标网站直连泄露。

### 3. 套用 VPN 分流策略并导入启用
1. **合入分流策略（见独立文件）**：将 **[references/routing-strategy.md](references/routing-strategy.md)** 中的 `proxy-groups`（两层核心代理组）和 `rules`（AI 域名排在国内 `GEOSITE,cn` / `GEOIP,CN` 之前，`MATCH` 兜底）合入这份静态 YAML。
2. **导入与激活配置**：
   - 将 YAML 放入手机后，在客户端「配置 / 文件 -> 导入」选择该文件，并**关闭该 Profile 的自动更新**（机场节点由配置内的 `proxy-providers` 更新，避免整份 YAML 被冲掉）。
   - 导入或编辑保存后，必须**返回配置列表点击选中这份文件**再启动 VPN（仅保存编辑器不会切换当前生效配置）。
3. **核对安卓客户端系统开关**：
   - **模式**：选择「规则模式」（严禁用全局模式替代分流）；
   - **自动路由系统流量**：开启；
   - **DNS 劫持**：开启；
   - **允许应用绕过 VPN**：关闭；
   - **IPv6**：关闭；
   - **系统 HTTP 代理**：TUN 开启后无需再开，避免重复代理；
   - **绕过私有网络**：需访问局域网设备时保留，否则可关闭以严格接管全部流量。

### 4. 启动与防漏验证
1. 启动 VPN 后进入代理组面板，确认 `🔰国外流量` 已选中 `美国 NTT 链式出口`，`↗️上游直连` 已选中可用机场节点。
2. 打开 `browserleaks.com` 检查：Public IP 与 WebRTC Public IP 必须一致且显示你的静态出口 IP。
3. IPv6 Leak 应无公网地址；DNS 检测不应出现国内本地运营商 DNS。
4. Local IP 中出现 `192.168.0.0/16`、`10.0.0.0/8`、`172.16.0.0/12` 属于局域网或 TUN 私有地址，不是公网泄露。
5. `udp: true` 仅允许客户端尝试转发 UDP，实际可用性取决于前置节点与静态出口支持情况。

---

## 附：备选模式——自有美国 VPS 直接出口

若自有美国 VPS 可直接国内连接出站，直接保留单节点出站即可，**不写 `dialer-proxy`，也不要与 SOCKS5 链式混设为默认出口**（VPS 直出的公网 IP 是 VPS 自身 IP）：

```yaml
proxies:
  - name: 美国 VPS 直连
    type: vless
    server: VPS_HOST
    port: 443
    uuid: VPS_UUID
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
