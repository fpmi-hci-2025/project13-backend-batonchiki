from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine, Column, String, Text, Numeric, DateTime, Integer, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel
from datetime import datetime
import uuid
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://app:app@localhost:5432/appdb")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    user_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)

class Item(Base):
    __tablename__ = "items"
    item_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    description = Column(Text)
    price = Column(Numeric(10, 2), nullable=False)

class Order(Base):
    __tablename__ = "orders"
    order_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.user_id"), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    status = Column(String, nullable=False)

class OrderItem(Base):
    __tablename__ = "order_items"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    order_id = Column(String, ForeignKey("orders.order_id"), nullable=False)
    item_id = Column(String, ForeignKey("items.item_id"), nullable=False)
    quantity = Column(Integer, nullable=False)


class UserCreate(BaseModel):
    email: str
    name: str

class UserResponse(BaseModel):
    user_id: str
    email: str
    name: str
    
    class Config:
        from_attributes = True

class ItemCreate(BaseModel):
    name: str
    description: str | None = None
    price: float

class ItemResponse(BaseModel):
    item_id: str
    name: str
    description: str | None = None
    price: float
    
    class Config:
        from_attributes = True

class ItemUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    price: float | None = None

class OrderItemCreate(BaseModel):
    item_id: str
    quantity: int

class OrderCreate(BaseModel):
    user_id: str
    items: list[OrderItemCreate]

class OrderResponse(BaseModel):
    order_id: str
    user_id: str
    created_at: datetime
    status: str
    
    class Config:
        from_attributes = True

# FastAPI app
app = FastAPI(
    title="Pharmacy API",
    description="API for pharmacy management system",
    version="1.0.0"
)

# Startup event to create tables
@app.on_event("startup")
async def startup_event():
    """Create tables on application startup"""
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        print(f"Warning: Could not create tables on startup: {e}")

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Routes - Users
@app.post("/api/users", response_model=UserResponse, status_code=201, tags=["Users"])
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    """Create a new user"""
    db_user = User(email=user.email, name=user.name)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.get("/api/users/{user_id}", response_model=UserResponse, tags=["Users"])
def get_user(user_id: str, db: Session = Depends(get_db)):
    """Get user by ID"""
    db_user = db.query(User).filter(User.user_id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

# Routes - Items
@app.get("/api/items", response_model=list[ItemResponse], tags=["Items"])
def list_items(db: Session = Depends(get_db)):
    """List all items"""
    return db.query(Item).all()

@app.post("/api/items", response_model=ItemResponse, status_code=201, tags=["Items"])
def create_item(item: ItemCreate, db: Session = Depends(get_db)):
    """Create a new item"""
    db_item = Item(name=item.name, description=item.description, price=item.price)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@app.get("/api/items/{item_id}", response_model=ItemResponse, tags=["Items"])
def get_item(item_id: str, db: Session = Depends(get_db)):
    """Get item by ID"""
    db_item = db.query(Item).filter(Item.item_id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")
    return db_item

@app.put("/api/items/{item_id}", response_model=ItemResponse, tags=["Items"])
def update_item(item_id: str, item: ItemUpdate, db: Session = Depends(get_db)):
    """Update an item"""
    db_item = db.query(Item).filter(Item.item_id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    if item.name:
        db_item.name = item.name
    if item.description:
        db_item.description = item.description
    if item.price:
        db_item.price = item.price
    
    db.commit()
    db.refresh(db_item)
    return db_item

@app.delete("/api/items/{item_id}", status_code=204, tags=["Items"])
def delete_item(item_id: str, db: Session = Depends(get_db)):
    """Delete an item"""
    db_item = db.query(Item).filter(Item.item_id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    db.delete(db_item)
    db.commit()
    return None

# Routes - Orders
@app.post("/api/orders", response_model=OrderResponse, status_code=201, tags=["Orders"])
def create_order(order: OrderCreate, db: Session = Depends(get_db)):
    """Create a new order"""
    # Check user exists
    db_user = db.query(User).filter(User.user_id == order.user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Create order
    db_order = Order(user_id=order.user_id, status="pending")
    db.add(db_order)
    db.flush()
    
    # Add order items
    for order_item in order.items:
        db_item = db.query(Item).filter(Item.item_id == order_item.item_id).first()
        if not db_item:
            raise HTTPException(status_code=404, detail=f"Item {order_item.item_id} not found")
        
        db_order_item = OrderItem(
            order_id=db_order.order_id,
            item_id=order_item.item_id,
            quantity=order_item.quantity
        )
        db.add(db_order_item)
    
    db.commit()
    db.refresh(db_order)
    return db_order

@app.get("/api/orders/{order_id}", response_model=OrderResponse, tags=["Orders"])
def get_order(order_id: str, db: Session = Depends(get_db)):
    """Get order by ID"""
    db_order = db.query(Order).filter(Order.order_id == order_id).first()
    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found")
    return db_order

# Health check
@app.get("/hello", tags=["Health"])
def hello():
    """Hello World endpoint for environment verification"""
    return {"message": "Hello World! Backend is running"}

@app.get("/health", tags=["Health"])
def health():
    """Health check endpoint"""
    return {"status": "ok"}
