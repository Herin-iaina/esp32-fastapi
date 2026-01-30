from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime

# --- Contacts & CRM ---

class ContactBase(BaseModel):
    code: str
    type: str  # 'customer', 'supplier', 'both'
    name: str
    legal_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    mobile: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state_province: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = "Madagascar"
    tax_id: Optional[str] = None
    stat: Optional[str] = None
    notes: Optional[str] = None
    is_active: bool = True

class ContactCreate(ContactBase):
    pass

class ContactResponse(ContactBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True

# --- Customers ---

class CustomerBase(BaseModel):
    contact_id: int
    payment_terms: int = 30
    credit_limit: float = 0
    discount_rate: float = 0
    customer_category: Optional[str] = None
    priority_level: str = "standard"

class CustomerCreate(CustomerBase):
    pass

class CustomerResponse(CustomerBase):
    id: int
    total_orders: int
    total_revenue: float
    last_order_date: Optional[datetime]
    average_order_value: float
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# --- Suppliers ---

class SupplierBase(BaseModel):
    contact_id: int
    payment_terms: int = 30
    minimum_order_amount: float = 0
    delivery_time_days: int = 7
    supplier_category: Optional[str] = None
    reliability_rating: float = 0
    is_preferred: bool = False

class SupplierCreate(SupplierBase):
    pass

class SupplierResponse(SupplierBase):
    id: int
    total_purchases: int
    total_spent: float
    last_purchase_date: Optional[datetime]
    average_delivery_time: Optional[float]
    on_time_delivery_rate: Optional[float]
    quality_rating: float
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# --- Products ---

class ProductBase(BaseModel):
    code: str
    name: str
    description: Optional[str] = None
    category: str
    unit: str = "unit"
    purchase_price: float = 0
    selling_price: float = 0
    current_stock: int = 0
    minimum_stock: int = 0
    maximum_stock: int = 0
    is_active: bool = True

class ProductCreate(ProductBase):
    pass

class ProductResponse(ProductBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# --- Orders ---

class OrderItemBase(BaseModel):
    product_id: int
    quantity: int
    unit_price: float
    discount_percent: float = 0
    line_total: float
    batch_id: Optional[int] = None
    notes: Optional[str] = None

class OrderItemCreate(OrderItemBase):
    pass

class OrderItemResponse(OrderItemBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class CustomerOrderBase(BaseModel):
    order_number: str
    customer_id: int
    expected_delivery_date: Optional[datetime] = None
    status: str = "pending"
    payment_status: str = "unpaid"
    subtotal: float = 0
    discount_amount: float = 0
    tax_amount: float = 0
    total_amount: float = 0
    paid_amount: float = 0
    notes: Optional[str] = None
    delivery_address: Optional[str] = None

class CustomerOrderCreate(CustomerOrderBase):
    items: List[OrderItemCreate]

class CustomerOrderResponse(CustomerOrderBase):
    id: int
    order_date: datetime
    created_at: datetime
    updated_at: datetime
    items: List[OrderItemResponse] = []

    class Config:
        from_attributes = True

# --- Incubators & IoT ---

class IncubatorBase(BaseModel):
    device_id: str
    name: str
    location: Optional[str] = None
    capacity: int
    status: str = "idle"

class IncubatorResponse(IncubatorBase):
    id: int
    is_online: bool
    last_seen: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class TelemetryBase(BaseModel):
    incubator_id: int
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    rotation_count: Optional[int] = None

class TelemetryResponse(TelemetryBase):
    id: int
    timestamp: datetime

    class Config:
        from_attributes = True

# --- Batches ---

class BatchBase(BaseModel):
    batch_number: str
    incubator_id: Optional[int] = None
    po_id: Optional[int] = None
    egg_quantity: int
    egg_supplier_id: Optional[int] = None
    start_date: datetime
    expected_hatch_date: Optional[datetime] = None
    status: str = "in_progress"

class BatchResponse(BatchBase):
    id: int
    actual_hatch_date: Optional[datetime]
    end_date: Optional[datetime]
    hatched_count: int
    failed_count: int
    hatch_rate: Optional[float]
    total_cost: float
    cost_per_chick: Optional[float]
    avg_temperature: Optional[float]
    avg_humidity: Optional[float]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
