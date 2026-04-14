from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from pydantic import BaseModel
from mock_data import inventory_items, orders, demand_forecasts, backlog_items, spending_summary, monthly_spending, category_spending, recent_transactions, purchase_orders

app = FastAPI(title="Factory Inventory Management System")

# Quarter mapping for date filtering
QUARTER_MAP = {
    'Q1-2025': ['2025-01', '2025-02', '2025-03'],
    'Q2-2025': ['2025-04', '2025-05', '2025-06'],
    'Q3-2025': ['2025-07', '2025-08', '2025-09'],
    'Q4-2025': ['2025-10', '2025-11', '2025-12']
}

def filter_by_month(items: list, month: Optional[str]) -> list:
    """Filter items by month/quarter based on order_date field"""
    if not month or month == 'all':
        return items

    if month.startswith('Q'):
        # Handle quarters
        if month in QUARTER_MAP:
            months = QUARTER_MAP[month]
            return [item for item in items if any(m in item.get('order_date', '') for m in months)]
    else:
        # Direct month match
        return [item for item in items if month in item.get('order_date', '')]

    return items

def apply_filters(items: list, warehouse: Optional[str] = None, category: Optional[str] = None,
                 status: Optional[str] = None) -> list:
    """Apply common filters to a list of items"""
    filtered = items

    if warehouse and warehouse != 'all':
        filtered = [item for item in filtered if item.get('warehouse') == warehouse]

    if category and category != 'all':
        filtered = [item for item in filtered if item.get('category', '').lower() == category.lower()]

    if status and status != 'all':
        filtered = [item for item in filtered if item.get('status', '').lower() == status.lower()]

    return filtered

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Data models
class InventoryItem(BaseModel):
    id: str
    sku: str
    name: str
    category: str
    warehouse: str
    quantity_on_hand: int
    reorder_point: int
    unit_cost: float
    location: str
    last_updated: str

class Order(BaseModel):
    id: str
    order_number: str
    customer: str
    items: List[dict]
    status: str
    order_date: str
    expected_delivery: str
    total_value: float
    actual_delivery: Optional[str] = None
    warehouse: Optional[str] = None
    category: Optional[str] = None

class DemandForecast(BaseModel):
    id: str
    item_sku: str
    item_name: str
    current_demand: int
    forecasted_demand: int
    trend: str
    period: str

class BacklogItem(BaseModel):
    id: str
    order_id: str
    item_sku: str
    item_name: str
    quantity_needed: int
    quantity_available: int
    days_delayed: int
    priority: str
    has_purchase_order: Optional[bool] = False

class PurchaseOrder(BaseModel):
    id: str
    backlog_item_id: str
    supplier_name: str
    quantity: int
    unit_cost: float
    expected_delivery_date: str
    status: str
    created_date: str
    notes: Optional[str] = None

class CreatePurchaseOrderRequest(BaseModel):
    backlog_item_id: str
    supplier_name: str
    quantity: int
    unit_cost: float
    expected_delivery_date: str
    notes: Optional[str] = None

# API endpoints
@app.get("/")
def root():
    return {"message": "Factory Inventory Management System API", "version": "1.0.0"}

@app.get("/api/inventory", response_model=List[InventoryItem])
def get_inventory(
    warehouse: Optional[str] = None,
    category: Optional[str] = None
):
    """Get all inventory items with optional filtering"""
    return apply_filters(inventory_items, warehouse, category)

@app.get("/api/inventory/{item_id}", response_model=InventoryItem)
def get_inventory_item(item_id: str):
    """Get a specific inventory item"""
    item = next((item for item in inventory_items if item["id"] == item_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item

@app.get("/api/orders", response_model=List[Order])
def get_orders(
    warehouse: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    month: Optional[str] = None
):
    """Get all orders with optional filtering"""
    filtered_orders = apply_filters(orders, warehouse, category, status)
    filtered_orders = filter_by_month(filtered_orders, month)
    return filtered_orders

@app.get("/api/orders/{order_id}", response_model=Order)
def get_order(order_id: str):
    """Get a specific order"""
    order = next((order for order in orders if order["id"] == order_id), None)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order

@app.get("/api/demand", response_model=List[DemandForecast])
def get_demand_forecasts():
    """Get demand forecasts"""
    return demand_forecasts

@app.get("/api/backlog", response_model=List[BacklogItem])
def get_backlog():
    """Get backlog items with purchase order status"""
    # Add has_purchase_order flag to each backlog item
    result = []
    for item in backlog_items:
        item_dict = dict(item)
        # Check if this backlog item has a purchase order
        has_po = any(po["backlog_item_id"] == item["id"] for po in purchase_orders)
        item_dict["has_purchase_order"] = has_po
        result.append(item_dict)
    return result

@app.get("/api/dashboard/summary")
def get_dashboard_summary(
    warehouse: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    month: Optional[str] = None
):
    """Get summary statistics for dashboard with optional filtering"""
    # Filter inventory
    filtered_inventory = apply_filters(inventory_items, warehouse, category)

    # Filter orders
    filtered_orders = apply_filters(orders, warehouse, category, status)
    filtered_orders = filter_by_month(filtered_orders, month)

    total_inventory_value = sum(item["quantity_on_hand"] * item["unit_cost"] for item in filtered_inventory)
    low_stock_items = len([item for item in filtered_inventory if item["quantity_on_hand"] <= item["reorder_point"]])
    pending_orders = len([order for order in filtered_orders if order["status"] in ["Processing", "Backordered"]])
    total_backlog_items = len(backlog_items)

    return {
        "total_inventory_value": round(total_inventory_value, 2),
        "low_stock_items": low_stock_items,
        "pending_orders": pending_orders,
        "total_backlog_items": total_backlog_items,
        "total_orders_value": sum(order["total_value"] for order in filtered_orders)
    }

@app.get("/api/spending/summary")
def get_spending_summary():
    """Get spending summary statistics"""
    return spending_summary

@app.get("/api/spending/monthly")
def get_monthly_spending():
    """Get monthly spending breakdown"""
    return monthly_spending

@app.get("/api/spending/categories")
def get_category_spending():
    """Get spending by category"""
    return category_spending

@app.get("/api/spending/transactions")
def get_recent_transactions():
    """Get recent transactions"""
    return recent_transactions

@app.get("/api/reports/quarterly")
def get_quarterly_reports():
    """Get quarterly performance reports"""
    # Calculate quarterly statistics from orders
    quarters = {}

    for order in orders:
        order_date = order.get('order_date', '')
        # Determine quarter
        if '2025-01' in order_date or '2025-02' in order_date or '2025-03' in order_date:
            quarter = 'Q1-2025'
        elif '2025-04' in order_date or '2025-05' in order_date or '2025-06' in order_date:
            quarter = 'Q2-2025'
        elif '2025-07' in order_date or '2025-08' in order_date or '2025-09' in order_date:
            quarter = 'Q3-2025'
        elif '2025-10' in order_date or '2025-11' in order_date or '2025-12' in order_date:
            quarter = 'Q4-2025'
        else:
            continue

        if quarter not in quarters:
            quarters[quarter] = {
                'quarter': quarter,
                'total_orders': 0,
                'total_revenue': 0,
                'delivered_orders': 0,
                'avg_order_value': 0
            }

        quarters[quarter]['total_orders'] += 1
        quarters[quarter]['total_revenue'] += order.get('total_value', 0)
        if order.get('status') == 'Delivered':
            quarters[quarter]['delivered_orders'] += 1

    # Calculate averages and fulfillment rate
    result = []
    for q, data in quarters.items():
        if data['total_orders'] > 0:
            data['avg_order_value'] = round(data['total_revenue'] / data['total_orders'], 2)
            data['fulfillment_rate'] = round((data['delivered_orders'] / data['total_orders']) * 100, 1)
        result.append(data)

    # Sort by quarter
    result.sort(key=lambda x: x['quarter'])
    return result

@app.get("/api/reports/monthly-trends")
def get_monthly_trends():
    """Get month-over-month trends"""
    months = {}

    for order in orders:
        order_date = order.get('order_date', '')
        if not order_date:
            continue

        # Extract month (format: YYYY-MM-DD)
        month = order_date[:7]  # Gets YYYY-MM

        if month not in months:
            months[month] = {
                'month': month,
                'order_count': 0,
                'revenue': 0,
                'delivered_count': 0
            }

        months[month]['order_count'] += 1
        months[month]['revenue'] += order.get('total_value', 0)
        if order.get('status') == 'Delivered':
            months[month]['delivered_count'] += 1

    # Convert to list and sort
    result = list(months.values())
    result.sort(key=lambda x: x['month'])
    return result

# Restocking Models
class RestockingRequest(BaseModel):
    budget: float
    warehouse: Optional[str] = None
    category: Optional[str] = None

class RestockingRecommendation(BaseModel):
    item_id: str
    sku: str
    name: str
    current_stock: int
    reorder_point: int
    recommended_quantity: int
    allocated_quantity: int
    unit_cost: float
    total_cost: float
    priority_score: float
    demand_trend: Optional[str] = None
    backlog_priority: Optional[str] = None
    is_partial: bool = False

class RestockingSummary(BaseModel):
    total_budget: float
    budget_allocated: float
    budget_remaining: float
    items_recommended: int
    items_covered: int
    recommendations: List[RestockingRecommendation]

def find_matching_demand_forecast(inventory_item, demand_forecasts):
    """Find matching demand forecast using fuzzy matching"""
    # Strategy 1: Exact SKU match
    match = next((d for d in demand_forecasts if d.get('item_sku') == inventory_item.get('sku')), None)
    if match:
        return match

    # Strategy 2: Name similarity matching
    item_name_words = inventory_item.get('name', '').lower().split()
    for forecast in demand_forecasts:
        forecast_name_words = forecast.get('item_name', '').lower().split()
        common_words = [word for word in item_name_words
                       if any(fw for fw in forecast_name_words if word in fw or fw in word)]
        if len(common_words) >= 2:
            return forecast

    return None

def find_matching_backlog_item(inventory_item, backlog_items):
    """Find matching backlog item using fuzzy matching"""
    # Strategy 1: Exact SKU match
    match = next((b for b in backlog_items if b.get('item_sku') == inventory_item.get('sku')), None)
    if match:
        return match

    # Strategy 2: Name similarity matching
    item_name_words = inventory_item.get('name', '').lower().split()
    for backlog in backlog_items:
        backlog_name_words = backlog.get('item_name', '').lower().split()
        common_words = [word for word in item_name_words
                       if any(bw for bw in backlog_name_words if word in bw or bw in word)]
        if len(common_words) >= 2:
            return backlog

    return None

def calculate_priority_score(item, demand_forecasts, backlog_items):
    """Calculate priority score for restocking item (0-100 points)"""
    score = 0

    # Factor 1: Stock level severity (0-40 points)
    if item.get('reorder_point', 0) > 0:
        stock_ratio = item.get('quantity_on_hand', 0) / item.get('reorder_point', 1)
        score += max(0, (1 - stock_ratio) * 40)

    # Factor 2: Demand trend (0-30 points)
    demand_forecast = find_matching_demand_forecast(item, demand_forecasts)
    if demand_forecast:
        trend = demand_forecast.get('trend', 'stable')
        if trend == 'increasing':
            score += 30
        elif trend == 'stable':
            score += 15
        # decreasing gets 0 points

    # Factor 3: Backlog urgency (0-30 points)
    backlog_item = find_matching_backlog_item(item, backlog_items)
    if backlog_item:
        priority = backlog_item.get('priority', 'low')
        if priority == 'high':
            score += 30
        elif priority == 'medium':
            score += 20
        elif priority == 'low':
            score += 10

    return score

def calculate_recommended_quantity(item, demand_forecasts):
    """Calculate recommended restock quantity based on reorder point and demand"""
    reorder_point = item.get('reorder_point', 0)
    current_stock = item.get('quantity_on_hand', 0)

    # Base restock amount to reach reorder point + safety stock
    base_restock = max(0, reorder_point - current_stock)
    safety_stock = int(reorder_point * 0.5)  # 50% of reorder point as safety stock

    # Adjust based on demand forecast
    demand_forecast = find_matching_demand_forecast(item, demand_forecasts)
    if demand_forecast:
        current_demand = demand_forecast.get('current_demand', 0)
        forecasted_demand = demand_forecast.get('forecasted_demand', 0)
        if forecasted_demand > current_demand:
            # Increase restock for growing demand
            demand_factor = (forecasted_demand / max(current_demand, 1)) - 1
            safety_stock = int(safety_stock * (1 + demand_factor))

    return base_restock + safety_stock

@app.post("/api/restocking/calculate", response_model=RestockingSummary)
def calculate_restocking(request: RestockingRequest):
    """Calculate budget-based restocking recommendations"""

    # Filter inventory by warehouse/category if specified
    filtered_inventory = apply_filters(inventory_items, request.warehouse, request.category)

    # Get items that need restocking (below reorder point)
    low_stock_items = [item for item in filtered_inventory
                      if item.get("quantity_on_hand", 0) <= item.get("reorder_point", 0)]

    if not low_stock_items:
        return RestockingSummary(
            total_budget=request.budget,
            budget_allocated=0,
            budget_remaining=request.budget,
            items_recommended=0,
            items_covered=0,
            recommendations=[]
        )

    # Calculate priority scores and recommended quantities
    prioritized_items = []
    for item in low_stock_items:
        priority_score = calculate_priority_score(item, demand_forecasts, backlog_items)
        recommended_quantity = calculate_recommended_quantity(item, demand_forecasts)
        total_cost = recommended_quantity * item.get('unit_cost', 0)

        # Get additional context
        demand_forecast = find_matching_demand_forecast(item, demand_forecasts)
        backlog_item = find_matching_backlog_item(item, backlog_items)

        prioritized_items.append({
            "item": item,
            "priority_score": priority_score,
            "recommended_quantity": recommended_quantity,
            "total_cost": total_cost,
            "demand_trend": demand_forecast.get('trend') if demand_forecast else None,
            "backlog_priority": backlog_item.get('priority') if backlog_item else None
        })

    # Sort by priority score (highest first)
    prioritized_items.sort(key=lambda x: x["priority_score"], reverse=True)

    # Allocate budget in priority order
    recommendations = []
    remaining_budget = request.budget

    for item_data in prioritized_items:
        item = item_data["item"]
        total_cost = item_data["total_cost"]

        if remaining_budget >= total_cost:
            # Full allocation
            recommendations.append(RestockingRecommendation(
                item_id=item["id"],
                sku=item["sku"],
                name=item["name"],
                current_stock=item["quantity_on_hand"],
                reorder_point=item["reorder_point"],
                recommended_quantity=item_data["recommended_quantity"],
                allocated_quantity=item_data["recommended_quantity"],
                unit_cost=item["unit_cost"],
                total_cost=total_cost,
                priority_score=item_data["priority_score"],
                demand_trend=item_data["demand_trend"],
                backlog_priority=item_data["backlog_priority"],
                is_partial=False
            ))
            remaining_budget -= total_cost
        else:
            # Partial allocation if budget allows at least 1 unit
            unit_cost = item.get('unit_cost', 0)
            if unit_cost > 0 and remaining_budget >= unit_cost:
                partial_quantity = int(remaining_budget // unit_cost)
                partial_cost = partial_quantity * unit_cost

                recommendations.append(RestockingRecommendation(
                    item_id=item["id"],
                    sku=item["sku"],
                    name=item["name"],
                    current_stock=item["quantity_on_hand"],
                    reorder_point=item["reorder_point"],
                    recommended_quantity=item_data["recommended_quantity"],
                    allocated_quantity=partial_quantity,
                    unit_cost=unit_cost,
                    total_cost=partial_cost,
                    priority_score=item_data["priority_score"],
                    demand_trend=item_data["demand_trend"],
                    backlog_priority=item_data["backlog_priority"],
                    is_partial=True
                ))
                remaining_budget = 0
                break

    budget_allocated = request.budget - remaining_budget

    return RestockingSummary(
        total_budget=request.budget,
        budget_allocated=budget_allocated,
        budget_remaining=remaining_budget,
        items_recommended=len(prioritized_items),
        items_covered=len(recommendations),
        recommendations=recommendations
    )

@app.get("/api/purchase-orders")
def get_purchase_orders():
    """Get all purchase orders"""
    return purchase_orders

@app.post("/api/restocking/approve")
def approve_restocking(recommendations: List[RestockingRecommendation]):
    """Approve and process restocking recommendations by creating purchase orders"""
    from datetime import datetime, timedelta

    created_orders = []
    for rec in recommendations:
        # Create purchase order
        po = {
            "id": f"PO-{datetime.now().strftime('%Y%m%d%H%M%S')}-{rec.item_id}",
            "backlog_item_id": "",  # Not directly linked to backlog
            "supplier_name": "Auto-Generated Restock",
            "quantity": rec.allocated_quantity,
            "unit_cost": rec.unit_cost,
            "expected_delivery_date": (datetime.now() + timedelta(days=7)).isoformat(),
            "status": "pending",
            "created_date": datetime.now().isoformat(),
            "notes": f"Budget-based restock for {rec.sku} (Priority: {rec.priority_score:.1f})"
        }

        created_orders.append(po)
        # In a real implementation, save to database
        # For mock data, append to the purchase_orders list
        purchase_orders.append(po)

    return {
        "message": f"Successfully created {len(created_orders)} purchase orders",
        "orders": created_orders,
        "total_items": len(recommendations),
        "status": "success"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
