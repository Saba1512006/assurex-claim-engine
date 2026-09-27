"""Pagination for lists filtered in Python (same attributes as Flask-SQLAlchemy's Pagination, for the pager macro)."""
from __future__ import annotations

import math


class ListPage:
    def __init__(self, items: list, page: int, per_page: int = 20):
        self.total, self.per_page = len(items), per_page
        self.pages = max(1, math.ceil(self.total / per_page))
        self.page = min(max(1, page), self.pages)
        start = (self.page - 1) * per_page
        self.items = items[start:start + per_page]
        self.has_prev, self.has_next = self.page > 1, self.page < self.pages
        self.prev_num, self.next_num = self.page - 1, self.page + 1
