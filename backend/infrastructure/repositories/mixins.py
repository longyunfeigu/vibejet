# input: SQLAlchemy Select 查询对象, ORM model_class（需含 deleted_at 列）
# output: SoftDeleteFilterMixin（仓储基类 mixin，统一“默认排除软删”规则）
# owner: wanhua.gu
# pos: 基础设施层 - 仓储 mixin（共享过滤规则）；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""Repository mixins shared across SQLAlchemy repositories.

The single source of truth for "default exclude soft-deleted rows". Repos whose
ORM model carries a ``deleted_at`` column inherit ``SoftDeleteFilterMixin`` so
that ``list``/``count`` (which funnel through ``_apply_filters``) and lookups
that opt in via ``_filter_active`` get the same behavior — no per-repo
re-derivation, no inconsistency between sibling repositories.
"""

from __future__ import annotations

from typing import Any, ClassVar


class SoftDeleteFilterMixin:
    """Provides the canonical "active rows only" filter.

    Concrete repository:
        class FooRepository(SoftDeleteFilterMixin, FooRepositoryABC):
            model_class = FooModel  # must expose `.deleted_at`

            def _apply_filters(self, query, *, kind=None, status=None):
                query = super()._apply_filters(query)  # excludes soft-deleted
                if kind:
                    query = query.where(FooModel.kind == kind)
                if status:
                    query = query.where(FooModel.status == status)
                return query

    Lookups that need an opt-out (``include_deleted=True`` on ``get_by_id`` /
    ``get_by_key``) call ``self._filter_active(query)`` conditionally instead
    of going through ``_apply_filters``.
    """

    model_class: ClassVar[Any]

    def _filter_active(self, query: Any) -> Any:
        """Add ``WHERE deleted_at IS NULL`` to the given query."""
        return query.where(self.model_class.deleted_at.is_(None))

    def _apply_filters(self, query: Any, **_filters: Any) -> Any:
        """Default: exclude soft-deleted rows. Subclasses override and call super()."""
        return self._filter_active(query)
