"""Stocks Blueprint — all routes and API endpoints."""

from datetime import datetime
from flask import Blueprint, jsonify, render_template, request
from blueprints.stocks.models import (
    init_stocks_db, create_trade, get_all_trades, delete_trade,
    create_fund, get_all_funds, delete_fund
)
from i18n import t

stocks_bp = Blueprint('stocks', __name__, url_prefix='/stocks')


@stocks_bp.route('/')
def index():
    """Render the main stocks dashboard page."""
    init_stocks_db()
    return render_template('stocks/dashboard.html')


@stocks_bp.route('/api/trades', methods=['GET'])
def api_get_trades():
    """Retrieve all stock trade records."""
    return jsonify(get_all_trades())


def calculate_average_cost(stock_name: str) -> float:
    """Calculate the average cost of a stock prior to the current transaction."""
    trades = get_all_trades()
    total_shares = 0
    total_cost = 0.0
    
    # trades is sorted by date ASC, id ASC
    for t in trades:
        if t['stock_name'] != stock_name:
            continue
        if t['type'] == 'buy':
            total_shares += t['shares']
            total_cost += t['total_amount']
        elif t['type'] == 'stock_dividend':
            total_shares += t['shares']
        elif t['type'] == 'sell':
            is_bulk = t.get('is_bulk', 0)
            avg_cost = total_cost / total_shares if total_shares > 0 else 0.0
            if is_bulk == 1:
                total_cost -= (t['shares'] * avg_cost)
            else:
                calculated_deduct = t['total_amount'] / 1.06
                max_deduct = t['shares'] * avg_cost
                actual_deduct = min(calculated_deduct, max_deduct) if (total_shares > 0 and max_deduct > 0) else calculated_deduct
                total_cost -= actual_deduct
            total_shares -= t['shares']
                
    return total_cost / total_shares if total_shares > 0 else 0.0


@stocks_bp.route('/api/trades', methods=['POST'])
def api_create_trade():
    """Create a new stock trade record."""
    data = request.get_json() or {}
    stock_name = data.get('stock_name', '').strip()
    stock_code = data.get('stock_code', '').strip()
    trade_type = data.get('type', '')  # buy / sell / stock_dividend
    shares = int(data.get('shares', 0))
    is_bulk = int(data.get('is_bulk', 0)) # 1 = bulk sell, 0 = normal

    if not stock_name or not stock_code or not trade_type or shares <= 0:
        return jsonify({'error': t('stocks.api.invalid_data')}), 400

    if trade_type == 'stock_dividend':
        total_amount = 0.0
    else:
        total_amount = float(data.get('total_amount', 0))

    date = data.get('date', '').strip()
    if not date:
        date = datetime.now().strftime('%Y-%m-%d')

    # Calculate average cost before inserting this sell transaction
    avg_cost = 0.0
    if trade_type == 'sell' and is_bulk == 1:
        avg_cost = calculate_average_cost(stock_name)

    trade_id = create_trade(stock_name, stock_code, date, trade_type, total_amount, shares, is_bulk)

    # Special behavior for 4-4 (賣出零股):
    # 資金資訊 DB 增加一筆：日期為今日系統時間，type 1="存入", type 2="賣出差額", 總金額 = 獲利額
    if trade_type == 'sell':
        if is_bulk == 1:
            # 大量賣出：獲利 = 賣出總金額 - (賣出股數 * 賣出前單股成本)
            cost_sell = shares * avg_cost
            profit_amount = total_amount - cost_sell
        else:
            # 一般賣出：獲利限制在 6%
            profit_amount = total_amount * 0.06

        create_fund(
            date=datetime.now().strftime('%Y-%m-%d'),
            type1='deposit',
            type2='sell_profit',
            stock_name=stock_name,
            total_amount=profit_amount,
            trade_id=trade_id
        )

    return jsonify({'id': trade_id}), 201


@stocks_bp.route('/api/trades/<int:trade_id>', methods=['DELETE'])
def api_delete_trade(trade_id):
    """Delete a stock trade record."""
    delete_trade(trade_id)
    return jsonify({'success': True})


@stocks_bp.route('/api/funds', methods=['GET'])
def api_get_funds():
    """Retrieve all fund records."""
    return jsonify(get_all_funds())


@stocks_bp.route('/api/funds', methods=['POST'])
def api_create_fund():
    """Create a new fund record."""
    data = request.get_json() or {}
    type1 = data.get('type1', '')  # deposit / withdraw
    type2 = data.get('type2', '')  # cash / dividend / sell_profit / settlement
    stock_name = data.get('stock_name', '').strip()
    total_amount = float(data.get('total_amount', 0))

    date = data.get('date', '').strip()
    if not date:
        date = datetime.now().strftime('%Y-%m-%d')

    if not type1 or not type2:
        return jsonify({'error': t('stocks.api.invalid_data')}), 400

    fund_id = create_fund(date, type1, type2, stock_name, total_amount)
    return jsonify({'id': fund_id}), 201


@stocks_bp.route('/api/funds/<int:fund_id>', methods=['DELETE'])
def api_delete_fund(fund_id):
    """Delete a fund record."""
    delete_fund(fund_id)
    return jsonify({'success': True})


@stocks_bp.route('/api/summary', methods=['GET'])
def api_summary():
    """Calculate and return investment and profit summary statistics."""
    funds = get_all_funds()

    # 4-7-1 投入總金額: type1 == 'deposit', type2 == 'cash' 總金額和
    #                 減去 type1 == 'withdraw', type2 == 'cash' 總金額和
    invested_deposit = sum(f['total_amount'] for f in funds if f['type1'] == 'deposit' and f['type2'] == 'cash')
    invested_withdraw = sum(f['total_amount'] for f in funds if f['type1'] == 'withdraw' and f['type2'] == 'cash')
    total_invested = invested_deposit - invested_withdraw

    # 4-7-2 股利總額: type1 == 'deposit', type2 == 'dividend' 總金額和
    total_dividends = sum(f['total_amount'] for f in funds if f['type1'] == 'deposit' and f['type2'] == 'dividend')

    # 4-7-3 賣出獲利: type1 == 'deposit', type2 == 'sell_profit' 總金額和，並加上常數 149431 (四捨五入至整數)
    total_sell_profit = round(sum(f['total_amount'] for f in funds if f['type1'] == 'deposit' and f['type2'] == 'sell_profit') + 149431)

    # 4-7-4 帳戶餘額: 交割款 + 存入現金 - 取出現金
    balance_settlement = sum(f['total_amount'] for f in funds if f['type1'] == 'deposit' and f['type2'] == 'settlement')
    balance_cash_deposit = sum(f['total_amount'] for f in funds if f['type1'] == 'deposit' and f['type2'] == 'cash')
    balance_cash_withdraw = sum(f['total_amount'] for f in funds if f['type1'] == 'withdraw' and f['type2'] == 'cash')
    account_balance = balance_settlement + balance_cash_deposit - balance_cash_withdraw

    # Return all funds for scrolling
    recent_funds = funds

    return jsonify({
        'total_invested': total_invested,
        'total_dividends': total_dividends,
        'total_sell_profit': total_sell_profit,
        'account_balance': account_balance,
        'recent_funds': recent_funds
    })
