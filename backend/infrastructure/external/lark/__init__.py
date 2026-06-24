# input: ./code_exchanger
# output: 飞书/Lark 授权码交换实现导出（LarkAuthCodeExchanger, LARK_OPEN_HOSTS）
# owner: wanhua.gu
# pos: 基础设施层 - 飞书/Lark 外部集成包导出（授权码 → 身份）；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""Feishu / Lark identity adapters."""

from .code_exchanger import LARK_OPEN_HOSTS, LarkAuthCodeExchanger

__all__ = ["LarkAuthCodeExchanger", "LARK_OPEN_HOSTS"]
