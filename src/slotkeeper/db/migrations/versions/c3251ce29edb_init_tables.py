"""init tables

Revision ID: c3251ce29edb
Revises: 
Create Date: 2025-11-11 16:14:34.140101

"""
from typing import Sequence, Union



# revision identifiers, used by Alembic.
revision: str = 'c3251ce29edb'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
