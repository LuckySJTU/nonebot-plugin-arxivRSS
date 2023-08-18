<div align="center">
  <a href="https://v2.nonebot.dev/store"><img src="https://github.com/A-kirami/nonebot-plugin-template/blob/resources/nbp_logo.png" width="180" height="180" alt="NoneBotPluginLogo"></a>
  <br>
  <p><img src="https://github.com/A-kirami/nonebot-plugin-template/blob/resources/NoneBotPlugin.svg" width="240" alt="NoneBotPluginText"></p>
</div>

<div align="center">

# nonebot-plugin-arxivRSS

_✨ 推送arxiv上每日最新论文的插件 ✨_


<a href="./LICENSE">
    <img src="https://img.shields.io/github/license/LuckySJTU/nonebot-plugin-arxivRSS.svg" alt="license">
</a>
<a href="https://pypi.python.org/pypi/nonebot-plugin-arxivRSS">
    <img src="https://img.shields.io/pypi/v/nonebot-plugin-arxivRSS.svg" alt="pypi">
</a>
<img src="https://img.shields.io/badge/python-3.8+-blue.svg" alt="python">

</div>


## 📖 介绍

这个插件调用arxiv的RSS订阅源，用于每天定时推送arxiv当天的新论文。目前仅支持私聊。

## 💿 安装

<details open>
<summary>使用 nb-cli 安装</summary>
在 nonebot2 项目的根目录下打开命令行, 输入以下指令即可安装

    nb plugin install nonebot-plugin-arxivRSS

</details>

<details>
<summary>使用包管理器安装</summary>
在 nonebot2 项目的插件目录下, 打开命令行, 根据你使用的包管理器, 输入相应的安装命令

<details>
<summary>pip</summary>

    pip install nonebot-plugin-arxivRSS
</details>
<details>
<summary>pdm</summary>

    pdm add nonebot-plugin-arxivRSS
</details>
<details>
<summary>poetry</summary>

    poetry add nonebot-plugin-arxivRSS
</details>
<details>
<summary>conda</summary>

    conda install nonebot-plugin-arxivRSS
</details>

打开 nonebot2 项目根目录下的 `pyproject.toml` 文件, 在 `[tool.nonebot]` 部分追加写入

    plugins = ["nonebot_plugin_arxivRSS"]

</details>


## 🎉 使用

⚠️**目前仅支持私聊**⚠️

首先使用`arxiv set <hh> <mm>`设定每日推送时间。

然后使用`arxiv add <category>`添加您关注的领域。`<category>`是arxiv官方对论文领域的分类，例如`cs`代表Computer Science，`cs.CL`代表Computation and Language。**`<category>`可以是单独的领域，也可以是多个领域，领域间使用空格分开。**[此处](https://arxiv.org/category_taxonomy)可以查看所有领域。

此时您已经完成了基本的设置，您将会在每日`<hh>:<mm>`收到来自arxivRSS的当日推送。

您还可以通过`arxiv push [category]`指令立刻获取arxivRSS的当日推送。如果不提供`[category]`，则推送您订阅中的所有领域。

### 所有指令

`arxiv` 显示所有指令

`arxiv add <category>` 添加`<category>`至您的订阅。

`arxiv del <category>` 从您的订阅中删除`<category>`。

`arxiv set <hh> <mm>` 设定您的推送时间为hh:mm

`arxiv cancel` 取消订阅。

`arxiv show` 查看您的订阅类别和推送时间。

`arxiv list` 查看所有可用的领域。

`arxiv push [category]` 立即获取`[category]`中所有类别的当日推送。如果`[category]`没有指定，那么会尝试推送您订阅中的所有领域。

### 效果图
如果有效果图的话
