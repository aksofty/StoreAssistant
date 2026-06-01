from app.models.base import Base
from app.models.source_base import SourceBase


class SourceYml(SourceBase, Base):
    __tablename__ = "source_yml"

 