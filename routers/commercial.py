from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from typing import List

from apps.database_configuration import db_manager, CustomerOrderModel, CustomerOrderItemModel, PurchaseOrderModel, PurchaseOrderItemModel, get_db
from models.crm_schemas import CustomerOrderCreate, CustomerOrderResponse

router = APIRouter()

@router.post("/orders", response_model=CustomerOrderResponse, status_code=status.HTTP_211_CREATED)
def create_customer_order(order: CustomerOrderCreate, db: Session = Depends(get_db)):
    # 1. Create order
    db_order = CustomerOrderModel(
        order_number=order.order_number,
        customer_id=order.customer_id,
        expected_delivery_date=order.expected_delivery_date,
        status=order.status,
        payment_status=order.payment_status,
        subtotal=order.subtotal,
        discount_amount=order.discount_amount,
        tax_amount=order.tax_amount,
        total_amount=order.total_amount,
        paid_amount=order.paid_amount,
        notes=order.notes,
        delivery_address=order.delivery_address
    )
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    
    # 2. Add items
    for item in order.items:
        db_item = CustomerOrderItemModel(
            order_id=db_order.id,
            **item.model_dump()
        )
        db.add(db_item)
    
    db.commit()
    db.refresh(db_order)
    return db_order

@router.get("/orders", response_model=List[CustomerOrderResponse])
def get_customer_orders(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    # Simple query, for better performance consider joining items in a real app
    return db.query(CustomerOrderModel).offset(skip).limit(limit).all()

@router.get("/orders/{order_id}", response_model=CustomerOrderResponse)
def get_customer_order(order_id: int, db: Session = Depends(get_db)):
    db_order = db.query(CustomerOrderModel).filter(CustomerOrderModel.id == order_id).first()
    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found")
    return db_order
