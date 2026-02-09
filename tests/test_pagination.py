"""
Tests for Pagination Utilities (backend/utils/pagination.py)

Covers PaginationParams, paginate(), paginate_dataframe(),
CursorPaginationParams, and create_pagination_links().
"""

import pytest
import pandas as pd

from backend.utils.pagination import (
    PaginationParams,
    PageMetadata,
    PaginatedResponse,
    paginate,
    paginate_dataframe,
    CursorPaginationParams,
    CursorPageMetadata,
    CursorPaginatedResponse,
    create_pagination_links,
)


class TestPaginationParams:
    """Tests for PaginationParams model."""

    def test_defaults(self):
        p = PaginationParams()
        assert p.page == 1
        assert p.page_size == 20

    def test_offset_property(self):
        p = PaginationParams(page=3, page_size=10)
        assert p.offset == 20

    def test_limit_property(self):
        p = PaginationParams(page_size=50)
        assert p.limit == 50

    def test_offset_page_one(self):
        p = PaginationParams(page=1, page_size=10)
        assert p.offset == 0


class TestPaginate:
    """Tests for paginate() function."""

    def test_basic_pagination(self):
        items = list(range(1, 11))  # [1..10]
        result = paginate(items, page=1, page_size=3)

        assert result["items"] == [1, 2, 3]
        assert result["metadata"]["total_items"] == 10
        assert result["metadata"]["total_pages"] == 4
        assert result["metadata"]["has_next"] is True
        assert result["metadata"]["has_previous"] is False

    def test_second_page(self):
        items = list(range(1, 11))
        result = paginate(items, page=2, page_size=3)

        assert result["items"] == [4, 5, 6]
        assert result["metadata"]["has_previous"] is True
        assert result["metadata"]["previous_page"] == 1
        assert result["metadata"]["next_page"] == 3

    def test_last_page(self):
        items = list(range(1, 11))
        result = paginate(items, page=4, page_size=3)

        assert result["items"] == [10]
        assert result["metadata"]["has_next"] is False
        assert result["metadata"]["next_page"] is None

    def test_empty_list(self):
        result = paginate([], page=1, page_size=10)
        assert result["items"] == []
        assert result["metadata"]["total_items"] == 0
        assert result["metadata"]["total_pages"] == 1

    def test_single_page(self):
        items = [1, 2, 3]
        result = paginate(items, page=1, page_size=10)
        assert result["items"] == [1, 2, 3]
        assert result["metadata"]["total_pages"] == 1

    def test_page_exceeds_total_clamped(self):
        items = list(range(5))
        result = paginate(items, page=100, page_size=3)
        # Should be clamped to last page
        assert result["metadata"]["page"] == 2

    def test_page_below_one_clamped(self):
        items = list(range(5))
        result = paginate(items, page=0, page_size=3)
        assert result["metadata"]["page"] == 1

    def test_page_size_below_one_defaults(self):
        items = list(range(5))
        result = paginate(items, page=1, page_size=0)
        assert result["metadata"]["page_size"] == 20

    def test_page_size_above_100_clamped(self):
        items = list(range(200))
        result = paginate(items, page=1, page_size=200)
        assert result["metadata"]["page_size"] == 100

    def test_custom_total_items(self):
        items = [1, 2, 3]
        result = paginate(items, page=1, page_size=3, total_items=100)
        assert result["metadata"]["total_items"] == 100
        assert result["metadata"]["total_pages"] == 34


class TestPaginateDataframe:
    """Tests for paginate_dataframe() function."""

    def test_basic_df_pagination(self):
        df = pd.DataFrame({"val": range(10)})
        result = paginate_dataframe(df, page=1, page_size=3)
        assert len(result["items"]) == 3
        assert result["metadata"]["total_items"] == 10
        assert result["metadata"]["total_pages"] == 4

    def test_df_second_page(self):
        df = pd.DataFrame({"val": range(10)})
        result = paginate_dataframe(df, page=2, page_size=3)
        assert len(result["items"]) == 3
        assert list(result["items"]["val"]) == [3, 4, 5]

    def test_df_page_clamp(self):
        df = pd.DataFrame({"val": range(5)})
        result = paginate_dataframe(df, page=100, page_size=3)
        assert result["metadata"]["page"] == 2

    def test_df_empty(self):
        df = pd.DataFrame({"val": []})
        result = paginate_dataframe(df, page=1, page_size=10)
        assert len(result["items"]) == 0
        assert result["metadata"]["total_pages"] == 1


class TestCreatePaginationLinks:
    """Tests for create_pagination_links() function."""

    def test_middle_page(self):
        links = create_pagination_links("/api/items", page=2, page_size=10, total_pages=5)
        assert "page=2" in links["self"]
        assert "page=1" in links["first"]
        assert "page=5" in links["last"]
        assert "page=3" in links["next"]
        assert "page=1" in links["prev"]

    def test_first_page_no_prev(self):
        links = create_pagination_links("/api/items", page=1, page_size=10, total_pages=3)
        assert "prev" not in links
        assert "next" in links

    def test_last_page_no_next(self):
        links = create_pagination_links("/api/items", page=3, page_size=10, total_pages=3)
        assert "next" not in links
        assert "prev" in links

    def test_with_query_params(self):
        links = create_pagination_links(
            "/api/items", page=1, page_size=10, total_pages=2,
            query_params={"sort": "name"}
        )
        assert "sort=name" in links["self"]

    def test_single_page(self):
        links = create_pagination_links("/api/items", page=1, page_size=10, total_pages=1)
        assert "next" not in links
        assert "prev" not in links


class TestCursorPaginationModels:
    """Tests for cursor-based pagination models."""

    def test_cursor_params_defaults(self):
        p = CursorPaginationParams()
        assert p.cursor is None
        assert p.limit == 20

    def test_cursor_metadata(self):
        m = CursorPageMetadata(has_next=True, next_cursor="abc123", count=20)
        assert m.has_next is True
        assert m.next_cursor == "abc123"
        assert m.count == 20

    def test_page_metadata_model(self):
        m = PageMetadata(
            page=1, page_size=20, total_items=100, total_pages=5,
            has_next=True, has_previous=False, next_page=2, previous_page=None
        )
        assert m.total_pages == 5
