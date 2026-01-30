from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, cast, Date
from typing import Dict, List
from datetime import datetime, timedelta

from apps.database_configuration import (
    db_manager, CustomerOrderModel, CustomerOrderItemModel, CustomerModel, SupplierModel,
    DataTempModel, ParameterDataModel, ContactModel, get_db
)

router = APIRouter()

@router.get("/dashboard/overview")
def get_dashboard_overview(db: Session = Depends(get_db)):
    """Statistiques principales du dashboard"""

    # Récupérer le dernier enregistrement de paramètres (incubation active)
    active_param = db.query(ParameterDataModel).order_by(desc(ParameterDataModel.id)).first()

    # Compter les capteurs actifs (données récentes dans les dernières 10 minutes)
    ten_minutes_ago = datetime.now() - timedelta(minutes=10)
    active_sensors = db.query(func.count(func.distinct(DataTempModel.sensor)))\
        .filter(DataTempModel.date_serveur >= ten_minutes_ago)\
        .scalar() or 0

    # Dernières données de température/humidité
    latest_data = db.query(DataTempModel).order_by(desc(DataTempModel.date_serveur)).first()

    # Stats CRM
    pending_orders = db.query(CustomerOrderModel).filter(CustomerOrderModel.status == 'pending').count()
    active_customers = db.query(CustomerModel).count()
    active_suppliers = db.query(SupplierModel).count()

    # Revenus du jour (dernières 24h)
    yesterday = datetime.now() - timedelta(days=1)
    daily_revenue = db.query(func.sum(CustomerOrderModel.total_amount))\
        .filter(CustomerOrderModel.order_date >= yesterday)\
        .scalar() or 0

    # Nombre de commandes du jour
    daily_orders_count = db.query(CustomerOrderModel)\
        .filter(CustomerOrderModel.order_date >= yesterday)\
        .count()

    # Calcul du nombre d'œufs et jours restants
    total_eggs = 0
    days_remaining = 0
    current_day = 0
    if active_param and active_param.start_date:
        end_date = active_param.start_date + timedelta(days=active_param.timetoclose)
        days_remaining = max(0, (end_date - datetime.now()).days)
        current_day = active_param.timetoclose - days_remaining
        total_eggs = active_param.rotation_count * 50  # Estimation

    return {
        "stats": {
            "activeIncubators": active_sensors,
            "totalEggs": total_eggs,
            "dailyRevenue": daily_revenue,
            "dailyOrdersCount": daily_orders_count,
            "pendingOrders": pending_orders,
            "activeSuppliers": active_suppliers,
            "activeCustomers": active_customers,
            "hatchRate": 87.5,
            "currentTemperature": latest_data.average_temperature if latest_data else 0,
            "currentHumidity": latest_data.average_humidity if latest_data else 0,
            "targetTemperature": active_param.temp_incubation if active_param else 37.5,
            "targetHumidity": active_param.humidity_target if active_param else 60.0,
            "daysRemaining": days_remaining,
            "currentDay": current_day,
            "totalDays": active_param.timetoclose if active_param else 21,
            "species": active_param.espece if active_param else "N/A"
        }
    }


@router.get("/dashboard/incubator-performance")
def get_incubator_performance(days: int = 7, db: Session = Depends(get_db)):
    """Données de température/humidité sur les derniers jours"""

    start_date = datetime.now() - timedelta(days=days)

    # Grouper par jour et calculer les moyennes
    daily_data = db.query(
        func.date(DataTempModel.date_serveur).label('date'),
        func.avg(DataTempModel.average_temperature).label('avg_temp'),
        func.avg(DataTempModel.average_humidity).label('avg_humidity'),
        func.count(DataTempModel.id).label('readings')
    ).filter(
        DataTempModel.date_serveur >= start_date
    ).group_by(
        func.date(DataTempModel.date_serveur)
    ).order_by(
        func.date(DataTempModel.date_serveur)
    ).all()

    result = []
    for row in daily_data:
        result.append({
            "date": row.date.strftime("%d %b") if row.date else "",
            "temp": round(row.avg_temp, 1) if row.avg_temp else 0,
            "humidity": round(row.avg_humidity, 1) if row.avg_humidity else 0,
            "readings": row.readings
        })

    # Si pas de données, retourner des données mockées pour la démo
    if not result:
        today = datetime.now()
        for i in range(days):
            d = today - timedelta(days=days-1-i)
            result.append({
                "date": d.strftime("%d %b"),
                "temp": 37.5,
                "humidity": 65,
                "readings": 0
            })

    return {"data": result}


@router.get("/dashboard/monthly-revenue")
def get_monthly_revenue(months: int = 7, db: Session = Depends(get_db)):
    """Revenus et coûts mensuels"""

    # Calculer les revenus par mois
    monthly_data = []
    today = datetime.now()

    for i in range(months):
        month_start = (today.replace(day=1) - timedelta(days=30*i)).replace(day=1)
        if i > 0:
            month_end = (today.replace(day=1) - timedelta(days=30*(i-1))).replace(day=1)
        else:
            month_end = today + timedelta(days=1)

        revenue = db.query(func.sum(CustomerOrderModel.total_amount))\
            .filter(CustomerOrderModel.order_date >= month_start)\
            .filter(CustomerOrderModel.order_date < month_end)\
            .scalar() or 0

        # Estimation des coûts (60% des revenus)
        costs = revenue * 0.6

        monthly_data.append({
            "month": month_start.strftime("%b"),
            "revenue": revenue,
            "costs": costs
        })

    monthly_data.reverse()
    return {"data": monthly_data}


@router.get("/dashboard/orders-by-status")
def get_orders_by_status(db: Session = Depends(get_db)):
    """Répartition des commandes par statut"""

    status_counts = db.query(
        CustomerOrderModel.status,
        func.count(CustomerOrderModel.id).label('count')
    ).group_by(CustomerOrderModel.status).all()

    status_colors = {
        'pending': '#fbbf24',
        'confirmed': '#3b82f6',
        'in_production': '#8b5cf6',
        'ready': '#10b981',
        'delivered': '#6b7280',
        'cancelled': '#ef4444'
    }

    status_labels = {
        'pending': 'En attente',
        'confirmed': 'Confirmé',
        'in_production': 'En production',
        'ready': 'Prêt',
        'delivered': 'Livré',
        'cancelled': 'Annulé'
    }

    result = []
    for status, count in status_counts:
        result.append({
            "name": status_labels.get(status, status),
            "value": count,
            "color": status_colors.get(status, '#6b7280')
        })

    # Si pas de données, retourner des données par défaut
    if not result:
        result = [
            {"name": "En attente", "value": 0, "color": "#fbbf24"},
            {"name": "Confirmé", "value": 0, "color": "#3b82f6"},
            {"name": "Livré", "value": 0, "color": "#6b7280"}
        ]

    return {"data": result}


@router.get("/dashboard/top-customers")
def get_top_customers(limit: int = 5, db: Session = Depends(get_db)):
    """Top clients par revenus"""

    # Joindre customers avec contacts pour avoir le nom
    top_customers = db.query(
        ContactModel.name,
        CustomerModel.total_orders,
        CustomerModel.total_revenue
    ).join(
        ContactModel, CustomerModel.contact_id == ContactModel.id
    ).order_by(
        desc(CustomerModel.total_revenue)
    ).limit(limit).all()

    result = []
    for name, orders, revenue in top_customers:
        result.append({
            "name": name,
            "orders": orders or 0,
            "revenue": revenue or 0
        })

    return {"data": result}


@router.get("/dashboard/supplier-performance")
def get_supplier_performance(db: Session = Depends(get_db)):
    """Performance des fournisseurs"""

    suppliers = db.query(
        ContactModel.name,
        SupplierModel.reliability_rating,
        SupplierModel.on_time_delivery_rate,
        SupplierModel.quality_rating
    ).join(
        ContactModel, SupplierModel.contact_id == ContactModel.id
    ).filter(
        ContactModel.is_active == True
    ).all()

    result = []
    for name, reliability, on_time, quality in suppliers:
        result.append({
            "name": name,
            "rating": reliability or 0,
            "onTime": (on_time or 0) * 100 if on_time and on_time <= 1 else (on_time or 0),
            "quality": quality or 0
        })

    return {"data": result}


@router.get("/dashboard/recent-orders")
def get_recent_orders(limit: int = 5, db: Session = Depends(get_db)):
    """Commandes récentes"""

    orders = db.query(
        CustomerOrderModel.order_number,
        CustomerOrderModel.total_amount,
        CustomerOrderModel.status,
        CustomerOrderModel.order_date,
        ContactModel.name.label('customer_name')
    ).join(
        CustomerModel, CustomerOrderModel.customer_id == CustomerModel.id
    ).join(
        ContactModel, CustomerModel.contact_id == ContactModel.id
    ).order_by(
        desc(CustomerOrderModel.order_date)
    ).limit(limit).all()

    status_labels = {
        'pending': 'En attente',
        'confirmed': 'Confirmé',
        'in_production': 'Production',
        'ready': 'Prêt',
        'delivered': 'Livré',
        'cancelled': 'Annulé'
    }

    result = []
    for order_number, amount, status, date, customer in orders:
        result.append({
            "id": order_number,
            "customer": customer,
            "amount": amount or 0,
            "status": status,
            "statusLabel": status_labels.get(status, status),
            "date": date.strftime("%Y-%m-%d") if date else ""
        })

    return {"data": result}


@router.get("/dashboard/active-batches")
def get_active_batches(db: Session = Depends(get_db)):
    """Lots d'incubation actifs (basé sur parameter_data)"""

    # Récupérer les paramètres actifs
    active_params = db.query(ParameterDataModel).order_by(desc(ParameterDataModel.id)).limit(4).all()

    result = []
    for i, param in enumerate(active_params):
        if param.start_date:
            end_date = param.start_date + timedelta(days=param.timetoclose)
            days_elapsed = (datetime.now() - param.start_date).days
            days_elapsed = max(0, min(days_elapsed, param.timetoclose))
            progress = int((days_elapsed / param.timetoclose) * 100)

            # Déterminer le statut
            status = 'on-track'
            if progress > 85:
                status = 'warning'

            result.append({
                "id": f"LOT-{param.id:03d}",
                "incubator": f"INC-{(i+1):02d}",
                "eggs": param.rotation_count * 50,
                "day": days_elapsed,
                "totalDays": param.timetoclose,
                "progress": progress,
                "status": status,
                "species": param.espece
            })

    return {"data": result}


@router.get("/dashboard/kpis")
def get_kpis(db: Session = Depends(get_db)):
    """KPIs détaillés pour la vue analytique"""

    # Calcul du coût par poussin (estimation)
    cost_per_chick = 1247  # À calculer depuis les vrais coûts

    # Marge moyenne
    total_revenue = db.query(func.sum(CustomerOrderModel.total_amount)).scalar() or 0
    estimated_costs = total_revenue * 0.615
    margin = ((total_revenue - estimated_costs) / total_revenue * 100) if total_revenue > 0 else 0

    # Délai moyen de livraison (jours entre commande et livraison)
    avg_delivery_days = 2.3  # À calculer depuis les vrais données

    return {
        "costPerChick": cost_per_chick,
        "costPerChickTrend": -5.2,
        "averageMargin": round(margin, 1),
        "marginTrend": 2.1,
        "avgDeliveryDays": avg_delivery_days,
        "deliveryTrend": 0.5
    }
