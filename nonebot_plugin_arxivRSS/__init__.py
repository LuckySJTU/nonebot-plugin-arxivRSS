from nonebot import get_driver

from .config import Config

import re
from pathlib import Path

import httpx
from nonebot import get_bot, get_driver, logger, on_command, require
from nonebot.adapters import Message
from nonebot.adapters.onebot.v11 import PrivateMessageEvent, GroupMessageEvent, MessageSegment, MessageEvent
from nonebot.matcher import Matcher
from nonebot.params import Arg, CommandArg
from nonebot.typing import T_State
from nonebot.plugin import PluginMetadata

import feedparser
import json
import time

global_config = get_driver().config
config = Config.parse_obj(global_config)

__plugin_meta__ = PluginMetadata(
    name="arxiv订阅",
    description="订阅arxiv指定领域每天更新的论文",
    usage="arxiv",
    type="application",
    config=Config,
    extra={
        "unique_name": "arxiv_subscribe",
        "example": "arxiv",
        "author": "Lucky <942546416@qq.com>",
        "version": "0.2.0",
    },
    homepage="https://github.com/LuckySJTU/nonebot-plugin-arxivRSS/",
    supported_adapters={"~onebot.v11"},
)

require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler
require("nonebot_plugin_localstore")
import nonebot_plugin_localstore as store

# subscribe = Path(__file__).parent / "subscribe.json"
# subscribe_list = json.loads(subscribe.read_text("utf-8")) if subscribe.is_file() else {}

subscribe = store.get_data_file("arxivRSS", "subscribe.json")
subscribe_list = json.loads(subscribe.read_text("utf-8")) if subscribe.is_file() else {}

#keywords = ["vsr","lrs2", "lrs3", "lrw", "visual speech", "avhubert", "lipread","lip-read", "contrastive", "wav2vec"]

def add_job(user_id):
    scheduler.add_job(
        push_all_arxiv_subscribe,
        "cron",
        args=[user_id, subscribe_list[user_id]['item'], subscribe_list[user_id]["keywords"]],
        id=f"arxiv_subscribe_{user_id}",
        replace_existing=True,
        hour=subscribe_list[user_id]["hour"],
        minute=subscribe_list[user_id]["minute"],
    )

def save_subscribe():
    subscribe.write_text(json.dumps(subscribe_list), encoding="utf-8")

driver = get_driver()
@driver.on_startup
async def subscribe_jobs():
    check_subscribe_list()
    for user_id in subscribe_list.keys():
        add_job(user_id)

def check_subscribe_list():
    for user_id in subscribe_list.keys():
        if "hour" not in subscribe_list[user_id]:
            subscribe_list[user_id]['hour'] = 0
        if "minute" not in subscribe_list[user_id]:
            subscribe_list[user_id]['minute'] = 0
        if "item" not in subscribe_list[user_id]:
            subscribe_list[user_id]['item'] = []
        if "keywords" not in subscribe_list[user_id]:
            subscribe_list[user_id]['keywords'] = []
    save_subscribe()

async def get_arxiv_rss(labels: str):
    news = feedparser.parse(f"http://arxiv.org/rss/{labels}")

    if "version" in news:
        return news.entries
    else:
        logger.info("Failed getting arxiv RSS, try mirror")
        news = feedparser.parse(f"http://arxiv.org/rss/{labels}?mirror=cn")
        if "version" in news:
            return news.entries
        logger.warning(f"Failed getting arxiv RSS with label {labels}")
        return

def get_author(author):
    pattern = re.compile(r'>.*?<')
    result = pattern.findall(author)
    author_name = "".join([au[1:-1] for au in result])
    return author_name

def get_summary(summary):
    pattern = re.compile(r'<p>.*?</p>')
    result = pattern.findall(summary.replace("\n"," "))
    author_name = "\n".join([au[3:-4] for au in result])
    return author_name

def check_keywords(text, keywords):
    if len(keywords)>0:
        pattern = re.compile(f'({"|".join(keywords)})', re.I)
        result = pattern.findall(text)
        #logger.info(result)
        return len(result)>0
    else:
        return False

def get_link(link):
    link = link.replace("cn.arxiv.org","arxiv.org")
    return link

async def get_arxiv_subscribe(user_id, label, keywords):
    entries = await get_arxiv_rss(label)
    if entries is None:
        return f"无效的类别 {label} 或网络异常。", None
    elif len(entries)==0:
        return f"类别{label}今日没有找到论文。", None
    else:
        msg_lists = []
        takeaway_list = []
        msg_list=[MessageSegment.node_custom(
            user_id=2174967552,
            nickname="ArxivRSS",
            content=Message(MessageSegment.text(f"类别{label}今日共找到{len(entries)}篇论文：\n")),
            )
        ]
        for i in range(len(entries)):
            title = entries[i].title
            author = get_author(entries[i].author)
            summary = get_summary(entries[i].summary)
            msg=f"[{i+1}]{title}\n"
            msg+=f"\n{author}\n"
            msg+=f"\n{summary}"
            msg_list.append(MessageSegment.node_custom(
                user_id=2174967552,
                nickname="ArxivRSS",
                content=Message(MessageSegment.text(msg)),
                )
            )
            if check_keywords(msg, keywords):
                takeaway_list.append(i+1)

            msg=get_link(entries[i].link)
            msg_list.append(MessageSegment.node_custom(
                user_id=2174967552,
                nickname="ArxivRSS",
                content=Message(MessageSegment.text(msg)),
                )
            )
            if (i+1)%20==0:
                msg_lists.append(msg_list)
                msg_list=[MessageSegment.node_custom(
                    user_id=2174967552,
                    nickname="ArxivRSS",
                    content=Message(MessageSegment.text(f"类别{label}今日共找到{len(entries)}篇论文：\n")),
                    )
                ]
            
        if len(msg_list)>1:
            msg_lists.append(msg_list)

        if len(takeaway_list)>0:
            takeaway = f"需要重点关注{takeaway_list}这些文章包含了预定的关键词。"
        else:
            takeaway = None

        return msg_lists, takeaway


async def push_all_arxiv_subscribe(user_id, labels, keywords):
    bot = get_bot()
    for label in labels:
        msg, takeaway = await get_arxiv_subscribe(user_id, label, keywords)
        if type(msg) is list:
            for m in msg:
                await bot.send_private_forward_msg(user_id=int(user_id),messages=m)
                time.sleep(5)
            if takeaway is not None:
                await bot.send_private_msg(user_id=int(user_id),message=takeaway)
        else:
            await bot.send_private_msg(user_id=int(user_id), message=msg)


arxiv_matcher = on_command("arxiv",aliases={"论文"},priority=5, block=True)
@arxiv_matcher.handle()
async def arxiv_main(
    event: MessageEvent, matcher: Matcher, args: Message = CommandArg()
):
    if isinstance(event, PrivateMessageEvent) and (cmdarg := args.extract_plain_text()):
        args = cmdarg.split()
        if args[0]=="add":
            # add category
            if len(args)<2:
                await matcher.finish(MessageSegment.text("在执行add指令时出现错误，您至少需要为其指定一个参数。"))
            else:
                user=str(event.user_id)
                if user not in subscribe_list:
                    await matcher.finish(MessageSegment.text("在执行add指令时出现错误，您首先需要指定一个订阅时间。"))
                else:
                    for cate in args[1:]:
                        if cate in subscribe_list[user]['item']:
                            await matcher.send(f"类别{cate}已经存在。")
                        else:
                            subscribe_list[user]['item'].append(cate)
                    add_job(user)
                    save_subscribe()
                    await matcher.finish(f"已添加{len(args)-1}个类别。")

        elif args[0]=="set":
            # set a time for subscription
            if len(args)<2 or (len(args)==2 and ":" not in args[1]):
                await matcher.finish(MessageSegment.text("在执行set指令时出现错误，您至少需要为其指定两个参数。"))
            else:
                user=str(event.user_id)
                if user not in subscribe_list:
                    subscribe_list[user]={"hour":0,"minute":0,"item":[],"keywords":[]}
                if len(args)==2:
                    time = args[1].split(":")
                    subscribe_list[user]['hour']=time[0]
                    subscribe_list[user]['minute']=time[1]
                else:
                    subscribe_list[user]['hour']=args[1]
                    subscribe_list[user]['minute']=args[2]

                add_job(user)
                save_subscribe()
                await matcher.finish(MessageSegment.text(f"已为您订阅在北京时间{args[1]}:{args[2]}的推送。"))

        elif args[0]=="cancel":
            # cancel a subscribe
            del subscribe_list[str(event.user_id)]
            save_subscribe()
            scheduler.remove_job(f"arxiv_subscribe_{event.user_id}")
            await matcher.finish(MessageSegment.text(f"已为您移除可能存在的订阅"))

        elif args[0] == "del":
            # remove a category from subscription
            if len(args)<2:
                await matcher.finish(MessageSegment.text("在执行del指令时出现错误，您至少需要为其指定一个参数。"))
            else:
                user=str(event.user_id)
                if user not in subscribe_list:
                    await matcher.finish(MessageSegment.text("在执行del指令时出现错误，您首先需要指定一个订阅时间。"))
                else:
                    for cate in args[1:]:
                        if cate not in subscribe_list[user]['item']:
                            await matcher.send(f"类别{cate}本就不存在。")
                        else:
                            subscribe_list[user]['item'].remove(cate)
                    add_job(user)
                    save_subscribe()
                    await matcher.finish(f"已移除{len(args)-1}个类别。")

        elif args[0] == "show":
            # show your subscription
            user = str(event.user_id)
            if user not in subscribe_list:
                await matcher.finish(MessageSegment.text("您还没有任何订阅。"))
            else:
                hh=subscribe_list[user]['hour']
                mm=subscribe_list[user]['minute']
                item=subscribe_list[user]['item']
                await matcher.finish(MessageSegment.text(f"用户{user}的订阅在{hh}:{mm}包含{item}中的内容。"))

        elif args[0] == "list":
            # list all supported arxiv Category
            await matcher.finish(MessageSegment.text("例如，cs.CL代表Computation and Language。\n您也可以使用cs获取所有cs类下的内容。\n完整列表请参考https://arxiv.org/category_taxonomy\n"))

        elif args[0] == "push":
            # push RSS right now
            user = str(event.user_id)
            if len(args)<2:
                # no category, try to use subscription
                if user in subscribe_list:
                    await push_all_arxiv_subscribe(user,subscribe_list[user]['item'],subscribe_list[user]['keywords'])
                    await matcher.finish()
                else:
                    await matcher.finish(MessageSegment.text("您至少需要指定一个类别，或至少订阅一个类别。"))
            else:
                await push_all_arxiv_subscribe(user,args[1:],subscribe_list[user]['keywords'])
        
        elif args[0] == "kw":
            if len(args)<2:
                msg = """
【arxiv kw add <keyword>】
Add keywords to your subsription. e.g. arxiv kw add self-supervised
Only one keyword each command

【arxiv kw show】
Show the keywords of your subsription.

【arxiv kw del <keyword>】
Delete a keyword from your subsription.
Only one at a time

【arxiv kw cancel】
Remove all the keywords of your subsription."""
                await matcher.finish(MessageSegment.text(msg))
            else:
                if args[1] == "add" :
                    # add keywords
                    if len(args)<3:
                        await matcher.finish(MessageSegment.text("在执行add指令时出现错误，您至少需要为其指定一个参数。"))
                    else:
                        user=str(event.user_id)
                        if user not in subscribe_list:
                            await matcher.finish(MessageSegment.text("在执行add指令时出现错误，您首先需要指定一个订阅时间。"))
                        else:
                            cate = ' '.join(args[2:])
                            if cate in subscribe_list[user]['keywords']:
                                await matcher.send(f"关键字{cate}已经存在。")
                            else:
                                subscribe_list[user]['keywords'].append(cate)
                                add_job(user)
                                save_subscribe()
                                await matcher.finish(f"已添加关键字{cate}。")
                elif args[1] == "show":
                    # show your keywords
                    user = str(event.user_id)
                    if user not in subscribe_list:
                        await matcher.finish(MessageSegment.text("您还没有任何订阅。"))
                    else:
                        await matcher.finish(MessageSegment.text(f"用户{user}关注的关键词有{subscribe_list[user]['keywords']}。"))
                elif args[1] == "del":
                    # remove a keyword from subscription
                    if len(args)<3:
                        await matcher.finish(MessageSegment.text("在执行del指令时出现错误，您至少需要为其指定一个参数。"))
                    else:
                        user=str(event.user_id)
                        if user not in subscribe_list:
                            await matcher.finish(MessageSegment.text("在执行del指令时出现错误，您首先需要指定一个订阅时间。"))
                        else:
                            cate = ' '.join(args[2:])
                            if cate not in subscribe_list[user]['keywords']:
                                await matcher.send(f"关键字{cate}本就不存在。")
                            else:
                                subscribe_list[user]['keywords'].remove(cate)
                                add_job(user)
                                save_subscribe()
                                await matcher.finish(f"已移除关键字{cate}。")
                elif args[1] == "cancel":
                    # cancel keywords
                    user = str(event.user_id)
                    if user not in subscribe_list:
                        await matcher.finish(MessageSegment.text("您还没有任何订阅。"))
                    subscribe_list[user]['keywords'] = []
                    add_job(user)
                    save_subscribe()
                    await matcher.finish(MessageSegment.text(f"已为您移除可能存在的关键词"))
        else:
            await matcher.finish(MessageSegment.text(f"未知的命令{cmdarg}"))
    else:
        msg = """arxiv <option> [args]

Private Conversation Only

Usage:
【arxiv add category】
Add a new category to your subscription. 
Category should be Arxiv Category like cs (for computer science) or cs.CL (for computation and language). 
Use "arxiv list" to get all supported categories.
You should use "arxiv set hh mm" to setup a subscription before you add any category

【arxiv del category】
Remove a category of your subscription.

【arxiv set hh mm】
Subscribe at hh:mm.

【arxiv cancel】
Cancel your subscription

【arxiv show】
List your subscription and time

【arxiv list】
List all supported arxiv category

【arxiv push [category]】
Push arxiv RSS right now. If category is not specified, will use user's subscription.
For example, "arxiv push" or "arxiv push cs.CL eess.AS"

【arxiv kw add <keyword>】
Add keywords to your subsription. e.g. arxiv kw add self-supervised
Only one keyword each command

【arxiv kw show】
Show the keywords of your subsription.

【arxiv kw del <keyword>】
Delete a keyword from your subsription.
Only one at a time

【arxiv kw cancel】
Remove all the keywords of your subsription.
"""
        await matcher.finish(MessageSegment.text(msg))

