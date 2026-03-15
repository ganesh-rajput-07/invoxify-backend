from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.database.connection import Base

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    wallet_id = Column(UUID(as_uuid=True), unique=True)
    is_email_public = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)
    reset_token = Column(String, nullable=True)
    reset_expiry = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship to wallet
    wallet = relationship("Wallet", back_populates="user", uselist=False)
    # Relationship to ideas
    ideas = relationship("Idea", back_populates="owner")
    
    # Relationship to problems
    problems = relationship("Problem", back_populates="author")
    problem_comments = relationship("ProblemComment", foreign_keys="ProblemComment.user_id", back_populates="author")
    problem_saves = relationship("ProblemSave", back_populates="user")

class Wallet(Base):
    __tablename__ = "wallets"

    wallet_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    balance = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="wallet")

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    from_wallet = Column(UUID(as_uuid=True), nullable=True) # None for system rewards/buys
    to_wallet = Column(UUID(as_uuid=True))
    amount = Column(Float)
    tx_hash = Column(String, unique=True)
    block_id = Column(Integer, ForeignKey("blocks.block_id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Idea(Base):
    __tablename__ = "ideas"

    idea_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, index=True)
    problem_statement = Column(Text)
    research_info = Column(Text)
    solution = Column(Text)
    keywords = Column(Text)
    category = Column(String)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    price = Column(Float, default=0.0)
    ipfs_hash = Column(String, nullable=True)
    problem_id = Column(UUID(as_uuid=True), ForeignKey("problems.id"), nullable=True) # Optional link to a specific Problem
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="ideas")
    problem = relationship("Problem", back_populates="proposed_solutions")

class IdeaPurchase(Base):
    __tablename__ = "idea_purchases"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    idea_id = Column(UUID(as_uuid=True), ForeignKey("ideas.idea_id"))
    buyer_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    price = Column(Float)
    tx_id = Column(UUID(as_uuid=True), ForeignKey("transactions.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

class Block(Base):
    __tablename__ = "blocks"

    block_id = Column(Integer, primary_key=True)
    hash = Column(String, unique=True)
    previous_hash = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)

class IdeaVector(Base):
    __tablename__ = "idea_vectors"

    idea_id = Column(UUID(as_uuid=True), primary_key=True)
    # Using simple array of floats if pgvector is not installed, otherwise we should use VECTOR
    # For a prototype, standard PostgreSQL Arrays or JSON can store it, or we can just calculate it 
    # and store as JSON string or array to be safe. We'll use JSON for simplicity unless pgvector is active.
    from sqlalchemy.dialects.postgresql import JSON
    embedding = Column(JSON) 

class UserFollow(Base):
    __tablename__ = "user_follows"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    follower_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    following_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

class EmailViewPurchase(Base):
    __tablename__ = "email_view_purchases"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    viewer_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    creator_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    price = Column(Float)
    tx_id = Column(UUID(as_uuid=True), ForeignKey("transactions.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

class Problem(Base):
    __tablename__ = "problems"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, index=True)
    description = Column(Text)
    category = Column(String)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

    author = relationship("User", back_populates="problems")
    comments = relationship("ProblemComment", back_populates="problem", cascade="all, delete-orphan")
    saves = relationship("ProblemSave", back_populates="problem", cascade="all, delete-orphan")
    proposed_solutions = relationship("Idea", back_populates="problem")

class ProblemComment(Base):
    __tablename__ = "problem_comments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    problem_id = Column(UUID(as_uuid=True), ForeignKey("problems.id"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    content = Column(Text)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("problem_comments.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    problem = relationship("Problem", back_populates="comments")
    author = relationship("User", foreign_keys=[user_id], back_populates="problem_comments")
    replies = relationship("ProblemComment", back_populates="parent", cascade="all, delete-orphan")
    parent = relationship("ProblemComment", back_populates="replies", remote_side=[id])

class ProblemSave(Base):
    __tablename__ = "problem_saves"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    problem_id = Column(UUID(as_uuid=True), ForeignKey("problems.id"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

    problem = relationship("Problem", back_populates="saves")
    user = relationship("User", back_populates="problem_saves")

class WithdrawalRequest(Base):
    __tablename__ = "withdrawal_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    amount = Column(Float)
    payment_method = Column(String) # 'UPI' or 'Bank'
    payment_details = Column(String) # UPI ID or Bank Details (name, acct, ifsc)
    status = Column(String, default="pending") # pending, approved, rejected
    admin_note = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class UserQuery(Base):
    __tablename__ = "user_queries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    subject = Column(String)
    message = Column(Text)
    is_resolved = Column(Boolean, default=False)
    admin_note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class SystemSetting(Base):
    __tablename__ = "system_settings"
    
    key = Column(String, primary_key=True)
    value = Column(String) # Stored as string, cast as needed
    description = Column(String, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
