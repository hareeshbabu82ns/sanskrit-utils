from sqlalchemy import Column, Integer, String
from sanskrit_utils.database import Base


class SanDicDhatuPata(Base):
    __tablename__ = 'dictEntries_content'

    docid = Column(Integer, primary_key=True)
    c0word = Column(String)
    c1hom = Column(String)
    c2desc = Column(String)
    c3origin = Column(String)
