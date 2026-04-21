# GitHub 上传步骤（一步一步）

当前已准备好的本地仓库目录：
- `C:\source\github-skills-bundle`

里面包含：
- `skills/data-science/medical-rag-data-cleaning`
- `skills/data-science/generic-rag-data-cleaning`

## 第1步：确认你的 GitHub 仓库地址
格式通常是二选一：
- HTTPS: `https://github.com/你的用户名/仓库名.git`
- SSH: `git@github.com:你的用户名/仓库名.git`

## 第2步：进入本地目录
在 WSL / Linux 终端里运行：

```bash
cd /mnt/c/source/github-skills-bundle
```

## 第3步：把文件提交到本地 git

```bash
git add .
git commit -m "feat: add Hermes RAG cleaning skills"
```

如果提示没有变更，可跳过 commit。

## 第4步：关联你的 GitHub 仓库
把下面的 `你的仓库地址` 换成真实地址：

```bash
git remote remove origin 2>/dev/null || true
git remote add origin 你的仓库地址
```

检查是否绑定成功：

```bash
git remote -v
```

## 第5步：推送到 GitHub

### 方案A：HTTPS + PAT token
```bash
git push -u origin main
```

这时如果弹出用户名/密码：
- Username：你的 GitHub 用户名
- Password：不要填 GitHub 登录密码，要填 PAT token

### 方案B：SSH
```bash
git push -u origin main
```

如果 SSH 已配置好，会直接推上去；如果没配置，会报权限错误。

## 第6步：验证
推送成功后，打开 GitHub 仓库页面，确认能看到：
- README.md
- bundle_manifest.json
- skills/data-science/medical-rag-data-cleaning
- skills/data-science/generic-rag-data-cleaning

## 第7步：其他电脑怎么使用
把仓库 clone 下来后，复制 skills 到：

```bash
~/.hermes/skills/data-science/
```

例如：

```bash
cp -r skills/data-science/medical-rag-data-cleaning ~/.hermes/skills/data-science/
cp -r skills/data-science/generic-rag-data-cleaning ~/.hermes/skills/data-science/
```
