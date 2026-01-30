from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Dict

from apps.database_configuration import db_manager, CustomerOrderModel, IncubatorModel, BatchModel, CustomerModel, SupplierModel, get_db

router = APIRouter()

@router.get("/dashboard/overview")
def get_dashboard_overview(db: Session = Depends(get_db)):
    """Simple summary for the dashboard overview card stats"""
    active_incubators = db.query(IncubatorModel).filter(IncubatorModel.status == 'running').count()
    total_eggs = db.query(func.sum(BatchModel.egg_quantity)).filter(BatchModel.status == 'in_progress').scalar() or 0
    pending_orders = db.query(CustomerOrderModel).filter(CustomerOrderModel.status == 'pending').count()
    active_customers = db.query(CustomerModel).count()
    active_suppliers = db.query(SupplierModel).count()
    
    # Simple daily revenue (last 24h)
    daily_revenue = db.query(func.sum(CustomerOrderModel.total_amount))\
        .filter(CustomerOrderModel.order_date >= func.now() - func.cast('1 day', func.interval))\
        .scalar() or 0

    return {
        "stats": {
            "activeIncubators": active_incubators,
            "totalEggs": total_eggs,
            "dailyRevenue": daily_revenue,
            "pendingOrders": pending_orders,
            "activeSuppliers": active_suppliers,
            "activeCustomers": active_customers,
            "hatchRate": 87.5 # Mocked for now until triggers/cron are implemented
        }
    }
