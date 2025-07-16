"""
FastAPI application for Digital ID Management Dashboard backend.

Features:
- Digital ID holder CRUD
- Unique numbers assignment/link/unlink
- Admin registration/login with invitation flow
- Super admin invitation management
- Linkage/unlinkage history
- Role-based authorization for endpoints
- JWT authentication flows
- Fully documented OpenAPI schema

Environment variables required: POSTGRES_URL, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB, POSTGRES_PORT

Run: uvicorn src.api.main:app --reload --host 0.0.0.0 --port 3001

Note:
If running as a module or via python main.py for local/deploy preview, you must ensure the FastAPI app is actually served on port 3001 and not the default 8000.

Optional direct start: python src/api/main.py    # (uses uvicorn programmatically, binds to 0.0.0.0:3001)

"""
import os
from datetime import datetime, timedelta
from enum import Enum as PyEnum
from typing import List, Optional

# Load environment variables from .env at backend startup (if present)
try:
    from dotenv import load_dotenv
    dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
    load_dotenv(dotenv_path, override=False)
except Exception as ex:
    print(f"Warning: Could not load .env file automatically. Please ensure environment variables are set. Details: {ex}")

from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import (Column, Integer, String, ForeignKey, DateTime, Enum as SAEnum, Boolean,
                        create_engine)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, scoped_session, Session

# Database config (MySQL)
# PUBLIC_INTERFACE
# Set these environment variables to configure connection to MySQL
# Example (in .env or exported in shell):
#   MYSQL_URL=localhost
#   MYSQL_USER=appuser
#   MYSQL_PASSWORD=dbuser123
#   MYSQL_DB=myapp
#   MYSQL_PORT=3306
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASS = os.getenv("MYSQL_PASSWORD", "password")
MYSQL_DB = os.getenv("MYSQL_DB", "digital_id")
MYSQL_HOST = os.getenv("MYSQL_URL", "localhost")
MYSQL_PORT = os.getenv("MYSQL_PORT", "3306")
# Compose SQLAlchemy connection string using env vars for portability.
MYSQL_URL = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASS}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}"

# JWT config
SECRET_KEY = os.getenv("JWT_SECRET", "very_secret_val")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 8   # 8 hours

# SQLAlchemy setup
Base = declarative_base()
engine = create_engine(MYSQL_URL, echo=False, future=True)
SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))


class RoleEnum(str, PyEnum):
    SUPERADMIN = "superadmin"
    ADMIN = "admin"


# ----------- Models (ORM) ----------
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String)
    full_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    is_invited = Column(Boolean, default=False)
    role = Column(SAEnum(RoleEnum), default=RoleEnum.ADMIN, nullable=False)
    invited_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    invitations = relationship("Invitation", back_populates="invitee", foreign_keys="Invitation.user_id")
    invited_admins = relationship("User", backref="inviter", remote_side=[id])
    histories = relationship("LinkageHistory", back_populates="admin")

class Invitation(Base):
    __tablename__ = "invitations"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=False)
    invite_token = Column(String, nullable=False)
    invited_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    accepted = Column(Boolean, default=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    invitee = relationship("User", foreign_keys=[user_id])

class DigitalIDHolder(Base):
    __tablename__ = "digital_id_holders"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    contact_email = Column(String, nullable=True)
    additional_info = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    unique_numbers = relationship("UniqueNumber", back_populates="holder")
    link_histories = relationship("LinkageHistory", back_populates="holder")

class UniqueNumber(Base):
    __tablename__ = "unique_numbers"
    id = Column(Integer, primary_key=True, index=True)
    number = Column(String, unique=True, index=True, nullable=False)
    holder_id = Column(Integer, ForeignKey("digital_id_holders.id"), nullable=True)
    assigned_at = Column(DateTime, nullable=True)
    holder = relationship("DigitalIDHolder", back_populates="unique_numbers")

class LinkageHistory(Base):
    __tablename__ = "linkage_history"
    id = Column(Integer, primary_key=True, index=True)
    holder_id = Column(Integer, ForeignKey("digital_id_holders.id"))
    unique_number_id = Column(Integer, ForeignKey("unique_numbers.id"))
    admin_id = Column(Integer, ForeignKey("users.id"))
    action = Column(String)  # 'link' or 'unlink'
    timestamp = Column(DateTime, default=datetime.utcnow)
    holder = relationship("DigitalIDHolder", back_populates="link_histories")
    admin = relationship("User", back_populates="histories")
    # no backref to UniqueNumber for history simplicity

# One time migration for dev
def init_db():
    Base.metadata.create_all(bind=engine)


# ----------- Auth Utilities -----------
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/token")


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> dict:
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

# Dependency for DB session per request
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Dependency for current user
def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"}
    )
    try:
        payload = decode_access_token(token)
        user_id: int = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        user = db.query(User).filter(User.id == user_id).first()
        if user is None or not user.is_active:
            raise credentials_exception
        return user
    except JWTError:
        raise credentials_exception

def get_current_active_user(current_user: User = Depends(get_current_user)):
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

def get_current_admin(current_user: User = Depends(get_current_user)):
    if current_user.role not in [RoleEnum.ADMIN, RoleEnum.SUPERADMIN]:
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return current_user

def get_current_superadmin(current_user: User = Depends(get_current_user)):
    if current_user.role != RoleEnum.SUPERADMIN:
        raise HTTPException(status_code=403, detail="Requires superadmin privileges")
    return current_user

# ----------- Pydantic Models -----------

class Token(BaseModel):
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(..., description='Type of token (bearer)')

class TokenData(BaseModel):
    sub: int
    role: RoleEnum

class InvitationCreate(BaseModel):
    email: EmailStr

class InvitationOut(BaseModel):
    id: int
    email: EmailStr
    invited_by: int
    created_at: datetime
    accepted: bool
    class Config:
        orm_mode = True

class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str]

class UserCreate(UserBase):
    password: str

class UserRegisterFromInvite(BaseModel):
    token: str
    full_name: Optional[str]
    password: str

class UserOut(UserBase):
    id: int
    role: RoleEnum
    is_active: bool
    class Config:
        orm_mode = True

class DigitalIDHolderBase(BaseModel):
    name: str
    contact_email: Optional[EmailStr]
    additional_info: Optional[str] = ''

class DigitalIDHolderCreate(DigitalIDHolderBase):
    pass

class DigitalIDHolderUpdate(DigitalIDHolderBase):
    pass

class DigitalIDHolderOut(DigitalIDHolderBase):
    id: int
    created_at: datetime
    class Config:
        orm_mode = True

class UniqueNumberBase(BaseModel):
    number: str

class UniqueNumberCreate(UniqueNumberBase):
    pass

class UniqueNumberOut(UniqueNumberBase):
    id: int
    holder_id: Optional[int]
    assigned_at: Optional[datetime]
    class Config:
        orm_mode = True

class LinkageAction(str, PyEnum):
    LINK = "link"
    UNLINK = "unlink"

class LinkageHistoryOut(BaseModel):
    id: int
    holder_id: int
    unique_number_id: int
    admin_id: int
    action: LinkageAction
    timestamp: datetime
    class Config:
        orm_mode = True

# ----------- FastAPI Setup -----------

tags_metadata = [
    {"name": "auth", "description": "Authentication, registration, login"},
    {"name": "admins", "description": "Admin & Superadmin management"},
    {"name": "holders", "description": "Digital ID Holder CRUD endpoints"},
    {"name": "unique_numbers", "description": "Assign/Unassign unique numbers to holders"},
    {"name": "history", "description": "View linkage/unlinkage history"},
]

app = FastAPI(
    title="Digital ID Management Backend",
    description="Backend API for managing digital ID holders, linkage, and admin management",
    version="1.0.0",
    openapi_tags=tags_metadata,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["health"])
def health_check():
    """Health check endpoint."""
    return {"message": "Healthy"}

# ----------- Auth & Admin Endpoints -----------

# PUBLIC_INTERFACE
@app.post("/api/token", response_model=Token, tags=["auth"], summary="Login as Admin or Superadmin")
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    """
    Login for admin or superadmin, returns JWT token on success.

    - **username**: Email address
    - **password**: User password
    """
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    token = create_access_token({"sub": user.id, "role": user.role})
    return {"access_token": token, "token_type": "bearer"}

# PUBLIC_INTERFACE
@app.post("/api/invite", response_model=InvitationOut, tags=["admins"], summary="Superadmin - Invite Admin")
def invite_admin(
    payload: InvitationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superadmin),
):
    """
    Invite an admin by email (only superadmin allowed). Re-invitation automatically reissues if not accepted.
    """
    user = db.query(User).filter(User.email == payload.email).first()
    invite_token = create_access_token({"email": payload.email}, expires_delta=timedelta(days=3))
    invitation = db.query(Invitation).filter(Invitation.email == payload.email).first()
    if invitation and not invitation.accepted:
        invitation.invite_token = invite_token
        invitation.invited_by = current_user.id
        invitation.created_at = datetime.utcnow()
        db.commit()
        db.refresh(invitation)
        # TODO: send re-invitation email here
        return invitation

    if user:
        raise HTTPException(400, "User already exists.")
    invite = Invitation(email=payload.email, invite_token=invite_token, invited_by=current_user.id)
    db.add(invite)
    db.commit()
    db.refresh(invite)
    # TODO: send invitation email here
    return invite

# PUBLIC_INTERFACE
@app.post("/api/register", response_model=Token, tags=["auth"], summary="Register from invitation")
def register_from_invite(data: UserRegisterFromInvite, db: Session = Depends(get_db)):
    """
    Register an admin when invited (using invitation token).
    """
    try:
        payload = decode_access_token(data.token)
        email: str = payload.get("email")
    except JWTError:
        raise HTTPException(400, "Invalid registration token.")
    invitation = db.query(Invitation).filter(Invitation.email == email, Invitation.accepted == False).first()
    if not invitation:
        raise HTTPException(400, "No valid invitation found for this email.")
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(400, "User already registered.")
    hashed_password = get_password_hash(data.password)
    user = User(
        email=email,
        hashed_password=hashed_password,
        full_name=data.full_name,
        role=RoleEnum.ADMIN,
        is_active=True,
        is_invited=True,
        invited_by=invitation.invited_by,
    )
    db.add(user)
    db.flush()
    invitation.accepted = True
    invitation.user_id = user.id
    db.commit()
    db.refresh(user)
    token = create_access_token({"sub": user.id, "role": user.role})
    return {"access_token": token, "token_type": "bearer"}

# PUBLIC_INTERFACE
@app.get("/api/users/me", response_model=UserOut, tags=["auth"], summary="Get Current User Profile")
def get_my_profile(current_user: User = Depends(get_current_active_user)):
    """
    Get info of the currently logged in user (admin or superadmin).
    """
    return current_user

# PUBLIC_INTERFACE
@app.get("/api/admins/", response_model=List[UserOut], tags=["admins"], summary="List admin users")
def list_admins(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superadmin)
):
    """
    List all admin users (superadmin only).
    """
    return db.query(User).filter(User.role == RoleEnum.ADMIN).all()

# ----------- Digital ID Holder CRUD -----------

# PUBLIC_INTERFACE
@app.post("/api/holders/", response_model=DigitalIDHolderOut, tags=["holders"], summary="Create Digital ID Holder")
def create_holder(
    data: DigitalIDHolderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    Create a new digital ID holder.
    """
    holder = DigitalIDHolder(**data.dict())
    db.add(holder)
    db.commit()
    db.refresh(holder)
    return holder

# PUBLIC_INTERFACE
@app.get("/api/holders/", response_model=List[DigitalIDHolderOut], tags=["holders"], summary="List Digital ID Holders")
def list_holders(
    db: Session = Depends(get_db),
    skip: int = Query(0, description="Pagination offset"),
    limit: int = Query(100, description="Pagination limit"),
    current_user: User = Depends(get_current_admin)
):
    """
    List all digital ID holders.
    """
    holders = db.query(DigitalIDHolder).offset(skip).limit(limit).all()
    return holders

# PUBLIC_INTERFACE
@app.get("/api/holders/{holder_id}", response_model=DigitalIDHolderOut, tags=["holders"], summary="Get Holder by ID")
def get_holder(holder_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_admin)):
    """
    Get a digital ID holder by holder_id.
    """
    holder = db.query(DigitalIDHolder).filter(DigitalIDHolder.id == holder_id).first()
    if not holder:
        raise HTTPException(404, "Holder not found")
    return holder

# PUBLIC_INTERFACE
@app.put("/api/holders/{holder_id}", response_model=DigitalIDHolderOut, tags=["holders"], summary="Update Holder")
def update_holder(
    holder_id: int,
    data: DigitalIDHolderUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    Update a digital ID holder.
    """
    holder = db.query(DigitalIDHolder).filter(DigitalIDHolder.id == holder_id).first()
    if not holder:
        raise HTTPException(404, "Holder not found")
    for k, v in data.dict(exclude_unset=True).items():
        setattr(holder, k, v)
    db.commit()
    db.refresh(holder)
    return holder

# PUBLIC_INTERFACE
@app.delete("/api/holders/{holder_id}", status_code=204, tags=["holders"], summary="Delete Holder")
def delete_holder(holder_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_admin)):
    """
    Delete a digital ID holder.
    """
    holder = db.query(DigitalIDHolder).filter(DigitalIDHolder.id == holder_id).first()
    if not holder:
        raise HTTPException(404, "Holder not found")
    db.delete(holder)
    db.commit()
    return None

# ----------- Unique Numbers (link/unlink/CRUD) -----------

# PUBLIC_INTERFACE
@app.post("/api/numbers/", response_model=UniqueNumberOut, tags=["unique_numbers"], summary="Create Unique Number")
def create_unique_number(
    data: UniqueNumberCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    Create a new unique number (unlinked).
    """
    if db.query(UniqueNumber).filter(UniqueNumber.number == data.number).first():
        raise HTTPException(400, "Unique number already exists.")
    num = UniqueNumber(number=data.number)
    db.add(num)
    db.commit()
    db.refresh(num)
    return num

# PUBLIC_INTERFACE
@app.get("/api/numbers/", response_model=List[UniqueNumberOut], tags=["unique_numbers"], summary="List Unique Numbers")
def list_unique_numbers(
    db: Session = Depends(get_db),
    skip: int = Query(0), limit: int = Query(100),
    holder_id: int = Query(None, description="Filter by holder id"),
    current_user: User = Depends(get_current_admin)
):
    """
    List all unique numbers, filtering by holder if holder_id provided.
    """
    q = db.query(UniqueNumber)
    if holder_id is not None:
        q = q.filter(UniqueNumber.holder_id == holder_id)
    return q.offset(skip).limit(limit).all()

# PUBLIC_INTERFACE
@app.post("/api/holders/{holder_id}/numbers/{number_id}/link", response_model=UniqueNumberOut, tags=["unique_numbers"], summary="Link Unique Number to Holder")
def link_number(
    holder_id: int,
    number_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    Link a unique number to a holder (assign).
    """
    holder = db.query(DigitalIDHolder).filter(DigitalIDHolder.id == holder_id).first()
    number = db.query(UniqueNumber).filter(UniqueNumber.id == number_id).first()
    if not holder or not number:
        raise HTTPException(404, "Holder or number not found")
    if number.holder_id is not None:
        raise HTTPException(400, "Number already linked.")
    number.holder_id = holder.id
    number.assigned_at = datetime.utcnow()
    db.add(LinkageHistory(
        holder_id=holder.id, unique_number_id=number.id, admin_id=current_user.id, action="link"
    ))
    db.commit()
    db.refresh(number)
    return number

# PUBLIC_INTERFACE
@app.post("/api/holders/{holder_id}/numbers/{number_id}/unlink", response_model=UniqueNumberOut, tags=["unique_numbers"], summary="Unlink Unique Number from Holder")
def unlink_number(
    holder_id: int,
    number_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    Unlink a unique number from a holder.
    """
    holder = db.query(DigitalIDHolder).filter(DigitalIDHolder.id == holder_id).first()
    number = db.query(UniqueNumber).filter(UniqueNumber.id == number_id, UniqueNumber.holder_id == holder_id).first()
    if not holder or not number:
        raise HTTPException(404, "Holder or number not found or not linked")
    number.holder_id = None
    number.assigned_at = None
    db.add(LinkageHistory(
        holder_id=holder.id, unique_number_id=number.id, admin_id=current_user.id, action="unlink"
    ))
    db.commit()
    db.refresh(number)
    return number

# ----------- History -----------

# PUBLIC_INTERFACE
@app.get("/api/history/", response_model=List[LinkageHistoryOut], tags=["history"], summary="Get Linkage History")
def get_history(
    db: Session = Depends(get_db),
    holder_id: int = Query(None),
    number_id: int = Query(None),
    admin_id: int = Query(None),
    skip: int = Query(0),
    limit: int = Query(100),
    current_user: User = Depends(get_current_admin)
):
    """
    Get holder/number/admin linkage & unlinkage history, optionally filtered.
    """
    q = db.query(LinkageHistory)
    if holder_id: q = q.filter(LinkageHistory.holder_id == holder_id)
    if number_id: q = q.filter(LinkageHistory.unique_number_id == number_id)
    if admin_id: q = q.filter(LinkageHistory.admin_id == admin_id)
    q = q.order_by(LinkageHistory.timestamp.desc())
    return q.offset(skip).limit(limit).all()

# =========================

# Run this once to generate tables (DEV ONLY, remove in prod)
try:
    init_db()
except Exception as ex:
    print("--- Warning: Could not init DB (probably already exists) ---", ex)

# ==========================================================
# Enable direct programmatic launch: python src/api/main.py
if __name__ == "__main__":
    import uvicorn
    port = 3001
    # Allow override with PORT env (e.g. in preview envs)
    try:
        port = int(os.getenv("PORT", "3001"))
    except Exception:
        port = 3001
    print(f"Starting server at 0.0.0.0:{port} (FOR DEV/DEPLOY PREVIEW)...")
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        factory=False
    )

