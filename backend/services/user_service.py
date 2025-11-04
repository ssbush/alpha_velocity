"""
User Service
Handles user registration, authentication, and profile management
"""

from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import datetime

from ..models.database import User, Portfolio, Holding, Transaction
from ..auth import get_password_hash, verify_password, UserRegistration, UserProfile


class UserService:
    """Service for user management operations"""

    def __init__(self, db_session: Session):
        self.db = db_session

    def create_user(self, registration: UserRegistration) -> User:
        """
        Create a new user account

        Args:
            registration: User registration data

        Returns:
            Created user object

        Raises:
            ValueError: If username or email already exists
        """
        # Check if username already exists
        existing_user = self.db.query(User).filter(
            (User.username == registration.username) | (User.email == registration.email)
        ).first()

        if existing_user:
            if existing_user.username == registration.username:
                raise ValueError("Username already exists")
            else:
                raise ValueError("Email already exists")

        # Create new user
        user = User(
            username=registration.username,
            email=registration.email,
            password_hash=get_password_hash(registration.password),
            first_name=registration.first_name,
            last_name=registration.last_name,
            is_active=True
        )

        try:
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)

            # Create a default portfolio for the user
            self._create_default_portfolio(user.id)

            return user
        except IntegrityError as e:
            self.db.rollback()
            raise ValueError(f"Error creating user: {str(e)}")

    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """
        Authenticate a user with username and password

        Args:
            username: Username or email
            password: Plain text password

        Returns:
            User object if authentication successful, None otherwise
        """
        user = self.db.query(User).filter(
            (User.username == username) | (User.email == username)
        ).first()

        if not user:
            return None

        if not verify_password(password, user.password_hash):
            return None

        if not user.is_active:
            return None

        return user

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        return self.db.query(User).filter(User.id == user_id).first()

    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        return self.db.query(User).filter(User.username == username).first()

    def get_user_profile(self, user_id: int) -> Optional[UserProfile]:
        """Get user profile data"""
        user = self.get_user_by_id(user_id)
        if not user:
            return None

        return UserProfile(
            id=user.id,
            username=user.username,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            is_active=user.is_active,
            created_at=user.created_at
        )

    def update_user_profile(self, user_id: int, **kwargs) -> Optional[User]:
        """
        Update user profile

        Args:
            user_id: User ID
            **kwargs: Fields to update (first_name, last_name, email)

        Returns:
            Updated user object
        """
        user = self.get_user_by_id(user_id)
        if not user:
            return None

        allowed_fields = ['first_name', 'last_name', 'email']
        for field, value in kwargs.items():
            if field in allowed_fields and value is not None:
                setattr(user, field, value)

        try:
            self.db.commit()
            self.db.refresh(user)
            return user
        except IntegrityError:
            self.db.rollback()
            raise ValueError("Email already exists")

    def change_password(self, user_id: int, current_password: str, new_password: str) -> bool:
        """
        Change user password

        Args:
            user_id: User ID
            current_password: Current password for verification
            new_password: New password to set

        Returns:
            True if successful, False otherwise
        """
        user = self.get_user_by_id(user_id)
        if not user:
            return False

        if not verify_password(current_password, user.password_hash):
            return False

        user.password_hash = get_password_hash(new_password)
        self.db.commit()
        return True

    def deactivate_user(self, user_id: int) -> bool:
        """Deactivate user account"""
        user = self.get_user_by_id(user_id)
        if not user:
            return False

        user.is_active = False
        self.db.commit()
        return True

    def _create_default_portfolio(self, user_id: int):
        """Create a default portfolio for new user"""
        default_portfolio = Portfolio(
            user_id=user_id,
            name="My Portfolio",
            description="Default portfolio",
            is_active=True
        )
        self.db.add(default_portfolio)
        self.db.commit()

    def get_user_portfolios(self, user_id: int) -> List[Portfolio]:
        """Get all portfolios for a user"""
        return self.db.query(Portfolio).filter(
            Portfolio.user_id == user_id,
            Portfolio.is_active == True
        ).order_by(Portfolio.created_at.desc()).all()

    def get_user_stats(self, user_id: int) -> dict:
        """Get user statistics"""
        portfolios = self.get_user_portfolios(user_id)

        total_holdings = self.db.query(Holding).join(Portfolio).filter(
            Portfolio.user_id == user_id,
            Portfolio.is_active == True
        ).count()

        total_transactions = self.db.query(Transaction).join(Portfolio).filter(
            Portfolio.user_id == user_id,
            Portfolio.is_active == True
        ).count()

        return {
            'total_portfolios': len(portfolios),
            'total_holdings': total_holdings,
            'total_transactions': total_transactions,
            'active_portfolios': [p.name for p in portfolios]
        }
