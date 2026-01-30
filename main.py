from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.core.message.components import Image
from astrbot.api.message_components import Node, Nodes, Plain
from .core.servant import *

@register("Mooncell Finder", "akidesuwa", "mooncell 网页查询", "0.1")
class MCF_plugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    async def initialize(self):
        """可选择实现异步的插件初始化方法，当实例化该插件类之后会自动调用该方法。"""
        logger.info("Mooncell Finder插件已初始化")

    # 注册指令的装饰器。指令名为 helloworld。注册成功后，发送 `/helloworld` 就会触发这个指令，并回复 `你好, {user_name}!`
    @filter.command("helloworld")
    async def helloworld(self, event: AstrMessageEvent):
        """这是一个 helloworld 指令""" # 这是 handler 的描述，将会被解析方便用户了解插件内容。建议填写。
        user_name = event.get_sender_name()
        message_str = event.message_str # 用户发的纯文本消息字符串
        message_chain = event.get_messages() # 用户所发的消息的消息链 # from astrbot.api.message_components import *
        logger.info(message_chain)
        yield event.plain_result(f"Hello, {user_name}, 你发了 {message_str}!") # 发送一条纯文本消息
        
    @filter.command("MCF从者")
    async def MCF_servant(self, event: AstrMessageEvent):
        """从者查询指令""" # 这是 handler 的描述，将会被解析方便用户了解插件内容。建议填写。
        user_name = event.get_sender_name()
        message_str = event.message_str # 用户发的纯文本消息字符串
        message_chain = event.get_messages() # 用户所发的消息的消息链 # from astrbot.api.message_components import *
        logger.info(message_chain)
        # 1. 按照 "MCF从者 " (包含空格) 分割
        # maxsplit=1 保证如果 XXX 里面有空格，不会被切碎
        keyword = message_str.split("MCF从者 ", 1)[1]
        yield event.plain_result(f"正在查找从者:{keyword}。") # 发送一条纯文本消息
        
        image_list = await find_in_mooncell_servant_2_imglist(keyword)
        # 准备合并转发的节点列表
        nodes = []
        # 1. 创建第一个节点：文字说明
        text_node = Node(
            uin=event.get_self_id(),
            name="Mooncell 查找结果",
            content=[Plain(f"已为您找到从者【{keyword}】的详细信息如下：")]
        )
        nodes.append(text_node)
        # 2. 遍历图片并放入节点
        if image_list:
            for img in image_list:
                if img is None:
                    continue
                
                # PIL Image -> Bytes
                buf = io.BytesIO()
                img.save(buf, format='PNG')
                img_bytes = buf.getvalue()
                
                # 创建图片节点
                # 注意：content 列表里直接放 Image 对象，不要套在 Plain 里面
                img_node = Node(
                    uin=event.get_self_id(),
                    name="Mooncell 数据截图",
                    content=[Image.fromBytes(img_bytes)] 
                )
                nodes.append(img_node)
        else:
            # 如果没搜到，添加一个提示节点
            nodes.append(Node(
                uin=event.get_self_id(),
                name="查找失败",
                content=[Plain("抱歉，未能在 Mooncell 找到该从者的相关截图。")]
            ))

        # 3. 封装并发送合并转发消息
        merge_forward_message = Nodes(nodes)
        yield event.chain_result([merge_forward_message])
        yield event.plain_result(f"查找完毕。")
    # @filter.command("MCF礼装")
    # async def MCF_concept(self, event: AstrMessageEvent):
    #     """礼装查询指令""" # 这是 handler 的描述，将会被解析方便用户了解插件内容。建议填写。
    #     user_name = event.get_sender_name()
    #     message_str = event.message_str # 用户发的纯文本消息字符串
    #     message_chain = event.get_messages() # 用户所发的消息的消息链 # from astrbot.api.message_components import *
    #     logger.info(message_chain)
    #     yield event.plain_result(f"功能未完成。。。。") # 发送一条纯文本消息
        
    # @filter.command("MCF活动")
    # async def MCF_event(self, event: AstrMessageEvent):
    #     """活动查询指令""" # 这是 handler 的描述，将会被解析方便用户了解插件内容。建议填写。
    #     user_name = event.get_sender_name()
    #     message_str = event.message_str # 用户发的纯文本消息字符串
    #     message_chain = event.get_messages() # 用户所发的消息的消息链 # from astrbot.api.message_components import *
    #     logger.info(message_chain)
    #     yield event.plain_result(f"功能未完成。。。。") # 发送一条纯文本消息
        

    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""
