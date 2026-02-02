import io

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.message_components import Node, Nodes, Plain
from astrbot.api.star import Context, Star, register
from astrbot.core.message.components import Image

from .core import ccode, craft, servant, trait


@register("Mooncell Finder", "akidesuwa", "mooncell 网页查询", "0.9")
class MCF_plugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        # 定义一个字典，用于存储不同类型的图片列表获取函数
        self.img_list_func_dict = {
            "从者": servant.find_in_mooncell_servant_2_imglist,
            "礼装": craft.find_in_mooncell_ce_2_imglist,
            "纹章": ccode.find_in_mooncell_cc_2_imglist,
            "特性": trait.find_in_mooncell_trait_2_imglist,
            "特性表格": trait.find_in_mooncell_trait_2_imglist_table,
        }

    async def initialize(self):
        """可选择实现异步的插件初始化方法，当实例化该插件类之后会自动调用该方法。"""
        logger.info("Mooncell Finder插件已初始化")

    async def _send_msg_func(self,event,image_list,key,keyword):
        """消息发送指令,用于发送合并转发消息。"""
        if keyword:
            msg1 = f"正在查找{key}:{keyword}。"
            msg2 = f"已为您找到{key}-{keyword}的详细信息如下："
        else:
            if key == "特性":
                msg1 = "正在查找【特性一览】表格。"
                msg2 = "已为您找到【特性一览】表格如下："

        yield event.plain_result(msg1)
        # 准备合并转发的节点列表
        nodes = []
        # 1. 创建第一个节点：文字说明
        text_node = Node(
            uin=event.get_self_id(),
            name="Mooncell 查找结果",
            content=[Plain(msg2)]
        )
        nodes.append(text_node)
        # 2. 遍历图片并放入节点
        if image_list:
            for img in image_list:
                if img is None:
                    continue

                # PIL Image -> Bytes
                buf = io.BytesIO()
                img.save(buf, format="PNG")
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
                content=[Plain(f"抱歉，未能在 Mooncell 找到该{key}的相关截图。")]
            ))

        # 3. 封装并发送合并转发消息
        merge_forward_message = Nodes(nodes)
        yield event.chain_result([merge_forward_message])
        yield event.plain_result("查找完毕。")

    @filter.command("MCF从者")
    async def MCF_servant(self, event: AstrMessageEvent):
        """从者查询指令,用于查询FGO相关的从者信息。"""
        message_str = event.message_str #
        message_chain = event.get_messages() # 用户所发的消息的消息链 # from astrbot.api.message_components import *
        logger.info(message_chain)
        keyword = message_str.replace("MCF从者", "", 1).strip()
        if keyword:
            image_list = await self.img_list_func_dict["从者"](keyword)
            logger.info("得到image_list")
            async for msg in self._send_msg_func(event, image_list, "从者", keyword):
                yield msg
            logger.info("成功发送")
        else:
            yield event.plain_result("从者查询关键词不可为空。")

    @filter.command("MCF礼装")
    async def MCF_craft(self, event: AstrMessageEvent):
        """礼装查询指令,用于查询FGO相关的礼装信息。"""
        message_str = event.message_str #
        message_chain = event.get_messages() # 用户所发的消息的消息链 # from astrbot.api.message_components import *
        logger.info(message_chain)
        keyword = message_str.replace("MCF礼装", "", 1).strip()
        if keyword:
            image_list = await self.img_list_func_dict["礼装"](keyword)
            logger.info("得到image_list")
            async for msg in self._send_msg_func(event, image_list, "礼装", keyword):
                yield msg
            logger.info("成功发送")
        else:
            yield event.plain_result("礼装查询关键词不可为空。")

    @filter.command("MCF纹章")
    async def MCF_ccode(self, event: AstrMessageEvent):
        """纹章查询指令,用于查询FGO相关的纹章信息。"""
        message_str = event.message_str #
        message_chain = event.get_messages() # 用户所发的消息的消息链 # from astrbot.api.message_components import *
        logger.info(message_chain)
        keyword = message_str.replace("MCF纹章", "", 1).strip()
        if keyword:
            image_list = await self.img_list_func_dict["纹章"](keyword)
            logger.info("得到image_list")
            async for msg in self._send_msg_func(event, image_list, "纹章", keyword):
                yield msg
            logger.info("成功发送")
        else:
            yield event.plain_result("纹章查询关键词不可为空。")

    @filter.command("MCF特性")
    async def MCF_event(self, event: AstrMessageEvent):
        """特性查询指令,用于查询FGO相关的特性信息。"""
        message_str = event.message_str #
        message_chain = event.get_messages() # 用户所发的消息的消息链 # from astrbot.api.message_components import *
        logger.info(message_chain)
        keyword = message_str.replace("MCF特性", "", 1).strip()
        if keyword:
            image_list = await self.img_list_func_dict["特性"](keyword)
        else:
            image_list = await self.img_list_func_dict["特性表格"]("属性：秩序·善")
        logger.info("得到image_list")
        async for msg in self._send_msg_func(event, image_list, "特性", keyword):
            yield msg
        logger.info("成功发送")


    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""
        logger.info("Mooncell Finder插件已停用。")
