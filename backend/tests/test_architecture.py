"""架构兜底测试：锁定 import 图表达不了的形状不变量。

DDD 依赖方向由 import-linter 强制（pyproject.toml [tool.importlinter]，
`uv run lint-imports`）；本文件只兜需要代码级断言的约束。
"""

import ast
import inspect

import application.ports.unit_of_work as uow_module

# AGENTS.md「Unit of Work Shape」：全局 UoW port 必须保持 repository-agnostic。
# 各应用服务需要的仓储用 service-local Protocol 声明（如 FileAssetUnitOfWork），
# 不往 UoW port 上挂属性。此测试变红时，走 Protocol 路线，而不是扩大白名单。
UOW_PUBLIC_API = {"commit", "rollback"}


def _public_class_members(cls: type) -> set[str]:
    # 同时取类命名空间与裸注解（`users: UserRepo` 不进 vars()，只进 __annotations__）
    names = set(vars(cls)) | set(getattr(cls, "__annotations__", {}))
    return {name for name in names if not name.startswith("_")}


def _public_self_assignments(cls: type) -> set[str]:
    """扫描类源码中 `self.<name> = ...` 形式的公开实例属性（vars() 抓不到）。"""
    tree = ast.parse(inspect.getsource(cls))
    found: set[str] = set()
    for node in ast.walk(tree):
        targets = (
            node.targets
            if isinstance(node, ast.Assign)
            else [node.target] if isinstance(node, (ast.AnnAssign, ast.AugAssign)) else []
        )
        for target in targets:
            if (
                isinstance(target, ast.Attribute)
                and isinstance(target.value, ast.Name)
                and target.value.id == "self"
                and not target.attr.startswith("_")
            ):
                found.add(target.attr)
    return found


def test_uow_port_module_stays_repository_agnostic() -> None:
    classes = [
        obj
        for _, obj in inspect.getmembers(uow_module, inspect.isclass)
        if obj.__module__ == uow_module.__name__
    ]
    assert classes, "application/ports/unit_of_work.py 中未找到任何类，测试对象丢失"
    for cls in classes:
        unexpected = (_public_class_members(cls) | _public_self_assignments(cls)) - UOW_PUBLIC_API
        assert not unexpected, (
            f"{cls.__name__} 出现白名单外的公开成员: {sorted(unexpected)}。"
            "不要把 repository 挂到全局 UoW；在应用服务侧定义 service-local Protocol"
            "（见 AGENTS.md「Unit of Work Shape」）。"
        )
