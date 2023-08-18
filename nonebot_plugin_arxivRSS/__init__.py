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
        "version": "0.1.0",
    },
    homepage="https://github.com/LuckySJTU/nonebot-plugin-arxivRSS/",
    supported_adapters={"~onebot.v11"},
)

require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler

subscribe = Path(__file__).parent / "subscribe.json"
subscribe_list = json.loads(subscribe.read_text("utf-8")) if subscribe.is_file() else {}

def save_subscribe():
    subscribe.write_text(json.dumps(subscribe_list), encoding="utf-8")

driver = get_driver()
@driver.on_startup
async def subscribe_jobs():
    for user_id, info in subscribe_list.items():
        scheduler.add_job(
            push_all_arxiv_subscribe,
            "cron",
            args=[user_id, info['item']],
            id=f"arxiv_subscribe_{user_id}",
            replace_existing=True,
            hour=info["hour"],
            minute=info["minute"],
        )

async def get_arxiv_rss(labels: str):
    news = feedparser.parse(f"http://arxiv.org/rss/{labels}")

    if not "bozo_exception" in news:
        return news.entries
    else:
        logger.warning(f"Failed getting arxiv RSS with label {labels}")
        return

def get_author(author):
    pattern = re.compile(r'>.*?<')
    result = pattern.findall(author)
    author_name = "".join([au[1:-1] for au in result])
    return author_name

def get_summary(summary):
    pattern = re.compile(r'<p>.*</p>')
    result = pattern.findall(summary.replace("\n"," "))
    author_name = "\n".join([au[3:-4] for au in result])
    return author_name

async def get_arxiv_subscribe(user_id: str, label: str):
    entries = await get_arxiv_rss(label)
    if entries is None:
        return f"Unsupported category {label} or network error"
    elif len(entries)==0:
        return f"类别{label}今日没有找到论文。"
    else:
        msg_lists = []
        msg_list=[MessageSegment.node_custom(
            user_id=2174967552,
            nickname="ArxivRSS",
            content=Message(MessageSegment.text(f"类别{label}今日共找到{len(entries)}篇论文：\n")),
            )
        ]
        for i in range(len(entries)):
            msg=f"[{i+1}]{entries[i].title}\n"
            msg+=f"\n{get_author(entries[i].author)}\n"
            msg+=f"\n{get_summary(entries[i].summary)}"
            msg_list.append(MessageSegment.node_custom(
                user_id=2174967552,
                nickname="ArxivRSS",
                content=Message(MessageSegment.text(msg)),
                )
            )
            msg=entries[i].link
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

        return msg_lists


async def push_all_arxiv_subscribe(user_id: str, labels: str):
    bot = get_bot()
    for label in labels:
        msg = await get_arxiv_subscribe(user_id, label)
        if type(msg) is list:
            for m in msg:
                await bot.send_private_forward_msg(user_id=int(user_id),messages=m)
                time.sleep(5)
        else:
            await bot.send_private_msg(user_id=int(user_id), message=msg)


arxiv_matcher = on_command("arxiv",aliases={"论文"},priority=10, block=True)
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
                    
                    save_subscribe()
                    await matcher.finish(f"已添加{len(args)-1}个类别。")

        elif args[0]=="set":
            # set a time for subscription
            if len(args)<3:
                await matcher.finish(MessageSegment.text("在执行set指令时出现错误，您至少需要为其指定两个参数。"))
            else:
                user=str(event.user_id)
                if user not in subscribe_list:
                    subscribe_list[user]={"hour":0,"minute":0,"item":[]}
                subscribe_list[user]['hour']=args[1]
                subscribe_list[user]['minute']=args[2]

                scheduler.add_job(
                    push_all_arxiv_subscribe,
                    "cron",
                    args=[user, subscribe_list[user]['item']],
                    id=f"arxiv_subscribe_{user}",
                    replace_existing=True,
                    hour=subscribe_list[user]["hour"],
                    minute=subscribe_list[user]["minute"],
                )
                save_subscribe()
                await matcher.finish(MessageSegment.text(f"已为您订阅在北京时间的corn {args[1]}:{args[2]}"))

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
                    await push_all_arxiv_subscribe(user,subscribe_list[user]['item'])
                    await matcher.finish()
                else:
                    await matcher.finish(MessageSegment.text("您至少需要指定一个类别，或拥有一个您的订阅。"))
            else:
                await push_all_arxiv_subscribe(user,args[1:])


        else:
            await matcher.finish(MessageSegment.text(f"未知的命令{cmdarg}"))
    else:
        msg = """arxiv <option> [args]

Private Conversation Only

<option>
add \t arxiv add category \t Add a new category to your subscription. Category should be Arxiv Category like cs (for computer science) or cs.CL (for computation and language).
del \t arxiv del category \t Remove a category of your subscribe
set \t arxiv set hh mm \t Subscribe at hh:mm
cancel \t arxiv cancel \t Cancel your subscription
show \t arxiv show \t List your subscribe and time
list \t arxiv list \t List all supported arxiv category
push \t arxiv push [category] \t Push arxiv RSS right now. If category is not specified, will use user's subscription.
"""
        await matcher.finish(MessageSegment.text(msg))

