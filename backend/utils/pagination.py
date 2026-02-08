"""
Pagination Utilities

Provides pagination helpers for API endpoints returning lists.
"""

from typing import TypeVar, Generic, List, Optional, Any
from pydantic import BaseModel, Field
from math import ceil
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')


class PaginationParams(BaseModel):
    """
    Pagination query parameters.
    
    Used as dependency in FastAPI endpoints.
    """
    page: int = Field(
        default=1,
        ge=1,
        description="Page number (1-indexed)"
    )
    page_size: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Number of items per page (1-100)"
    )
    
    @property
    def offset(self) -> int:
        """Calculate offset for database queries"""
        return (self.page - 1) * self.page_size
    
    @property
    def limit(self) -> int:
        """Alias for page_size"""
        return self.page_size


class PageMetadata(BaseModel):
    """Pagination metadata included in responses"""
    page: int = Field(description="Current page number")
    page_size: int = Field(description="Items per page")
    total_items: int = Field(description="Total number of items")
    total_pages: int = Field(description="Total number of pages")
    has_next: bool = Field(description="Whether there is a next page")
    has_previous: bool = Field(description="Whether there is a previous page")
    next_page: Optional[int] = Field(description="Next page number (if exists)")
    previous_page: Optional[int] = Field(description="Previous page number (if exists)")


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Generic paginated response wrapper.
    
    Example:
        PaginatedResponse[MomentumScore](
            items=[...],
            metadata=PageMetadata(...)
        )
    """
    items: List[T] = Field(description="List of items for current page")
    metadata: PageMetadata = Field(description="Pagination metadata")
    
    class Config:
        # Allow arbitrary types (for generic T)
        arbitrary_types_allowed = True


def paginate(
    items: List[Any],
    page: int = 1,
    page_size: int = 20,
    total_items: Optional[int] = None
) -> dict:
    """
    Paginate a list of items.
    
    Args:
        items: Full list of items or subset to paginate
        page: Current page number (1-indexed)
        page_size: Number of items per page
        total_items: Total number of items (if different from len(items))
    
    Returns:
        Dictionary with 'items' and 'metadata' keys
    
    Example:
        >>> stocks = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        >>> result = paginate(stocks, page=2, page_size=3)
        >>> result['items']
        [4, 5, 6]
        >>> result['metadata']['total_pages']
        4
    """
    # Validate inputs
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 20
    if page_size > 100:
        page_size = 100
    
    # Use provided total or calculate from items
    if total_items is None:
        total_items = len(items)
    
    # Calculate pagination
    total_pages = ceil(total_items / page_size) if total_items > 0 else 1
    
    # Ensure page doesn't exceed total pages
    if page > total_pages:
        page = total_pages
    
    # Calculate slice indices
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    
    # Get items for current page
    paginated_items = items[start_idx:end_idx]
    
    # Build metadata
    metadata = {
        'page': page,
        'page_size': page_size,
        'total_items': total_items,
        'total_pages': total_pages,
        'has_next': page < total_pages,
        'has_previous': page > 1,
        'next_page': page + 1 if page < total_pages else None,
        'previous_page': page - 1 if page > 1 else None
    }
    
    logger.debug(
        f"Paginated {total_items} items: page {page}/{total_pages}, "
        f"showing {len(paginated_items)} items"
    )
    
    return {
        'items': paginated_items,
        'metadata': metadata
    }


def paginate_dataframe(
    df,  # pandas DataFrame
    page: int = 1,
    page_size: int = 20
) -> dict:
    """
    Paginate a pandas DataFrame.
    
    Args:
        df: pandas DataFrame to paginate
        page: Current page number (1-indexed)
        page_size: Number of rows per page
    
    Returns:
        Dictionary with 'items' (DataFrame) and 'metadata' keys
    """
    total_items = len(df)
    
    # Validate inputs
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 20
    if page_size > 100:
        page_size = 100
    
    # Calculate pagination
    total_pages = ceil(total_items / page_size) if total_items > 0 else 1
    
    # Ensure page doesn't exceed total pages
    if page > total_pages:
        page = total_pages
    
    # Calculate slice indices
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    
    # Get rows for current page
    paginated_df = df.iloc[start_idx:end_idx]
    
    # Build metadata
    metadata = {
        'page': page,
        'page_size': page_size,
        'total_items': total_items,
        'total_pages': total_pages,
        'has_next': page < total_pages,
        'has_previous': page > 1,
        'next_page': page + 1 if page < total_pages else None,
        'previous_page': page - 1 if page > 1 else None
    }
    
    return {
        'items': paginated_df,
        'metadata': metadata
    }


class CursorPaginationParams(BaseModel):
    """
    Cursor-based pagination parameters.
    
    Alternative to offset pagination for large datasets.
    More efficient for real-time data.
    """
    cursor: Optional[str] = Field(
        default=None,
        description="Cursor from previous response (for next page)"
    )
    limit: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Number of items to return (1-100)"
    )


class CursorPageMetadata(BaseModel):
    """Cursor pagination metadata"""
    has_next: bool = Field(description="Whether there are more items")
    next_cursor: Optional[str] = Field(description="Cursor for next page")
    count: int = Field(description="Number of items in current response")


class CursorPaginatedResponse(BaseModel, Generic[T]):
    """
    Generic cursor-paginated response wrapper.
    
    Used for endpoints with large, frequently-changing datasets.
    """
    items: List[T] = Field(description="List of items")
    metadata: CursorPageMetadata = Field(description="Cursor pagination metadata")
    
    class Config:
        arbitrary_types_allowed = True


def create_pagination_links(
    base_url: str,
    page: int,
    page_size: int,
    total_pages: int,
    query_params: dict = None
) -> dict:
    """
    Create pagination links for HATEOAS-style responses.
    
    Args:
        base_url: Base URL for the endpoint
        page: Current page
        page_size: Items per page
        total_pages: Total number of pages
        query_params: Additional query parameters to include
    
    Returns:
        Dictionary with 'self', 'first', 'last', 'next', 'prev' links
    """
    if query_params is None:
        query_params = {}
    
    def build_link(page_num: int) -> str:
        params = {**query_params, 'page': page_num, 'page_size': page_size}
        param_str = '&'.join(f"{k}={v}" for k, v in params.items())
        return f"{base_url}?{param_str}"
    
    links = {
        'self': build_link(page),
        'first': build_link(1),
        'last': build_link(total_pages)
    }
    
    if page < total_pages:
        links['next'] = build_link(page + 1)
    
    if page > 1:
        links['prev'] = build_link(page - 1)
    
    return links
