from collections import defaultdict
from datetime import date
from database import get_connection, get_report_totals


def ensure_investment_schema():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS investor_profiles (
                    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                    objective VARCHAR(40) NOT NULL DEFAULT 'growth',
                    horizon_years INTEGER NOT NULL DEFAULT 5,
                    risk_comfort VARCHAR(20) NOT NULL DEFAULT 'moderate',
                    loss_reaction VARCHAR(30) NOT NULL DEFAULT 'hold',
                    emergency_months NUMERIC(6,2) NOT NULL DEFAULT 0,
                    monthly_investment NUMERIC(18,2) NOT NULL DEFAULT 0,
                    profile VARCHAR(20) NOT NULL DEFAULT 'Moderate',
                    score INTEGER NOT NULL DEFAULT 0,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS investments (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    name VARCHAR(180) NOT NULL,
                    symbol VARCHAR(40),
                    asset_type VARCHAR(40) NOT NULL,
                    sector VARCHAR(100),
                    quantity NUMERIC(20,6) NOT NULL DEFAULT 0,
                    average_cost NUMERIC(18,4) NOT NULL DEFAULT 0,
                    current_price NUMERIC(18,4) NOT NULL DEFAULT 0,
                    currency VARCHAR(10) NOT NULL DEFAULT 'INR',
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_investments_user ON investments(user_id)")
            cur.execute("ALTER TABLE investments ADD COLUMN IF NOT EXISTS market_change_pct NUMERIC(12,4)")
            cur.execute("ALTER TABLE investments ADD COLUMN IF NOT EXISTS market_price_updated_at TIMESTAMP")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS investment_watchlist (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    name VARCHAR(180) NOT NULL,
                    symbol VARCHAR(40),
                    asset_type VARCHAR(40) NOT NULL DEFAULT 'Stock',
                    note TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_watchlist_user ON investment_watchlist(user_id)")
        conn.commit()
    finally:
        conn.close()


def _num(v, default=0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def calculate_profile(objective, horizon_years, risk_comfort, loss_reaction):
    score = 0
    score += {'preserve': 0, 'income': 1, 'growth': 2}.get(objective, 1)
    h = int(horizon_years or 0)
    score += 0 if h < 3 else 1 if h < 7 else 2
    score += {'low': 0, 'moderate': 1, 'high': 2}.get(risk_comfort, 1)
    score += {'sell': 0, 'hold': 1, 'add': 2}.get(loss_reaction, 1)
    profile = 'Conservative' if score <= 2 else 'Moderate' if score <= 5 else 'Growth'
    return profile, score


def model_allocation(profile):
    # Educational model allocation only; never security-level advice.
    return {
        'Conservative': {'Equity': 25, 'Fixed income': 45, 'Gold': 10, 'Cash / liquid': 20},
        'Moderate': {'Equity': 50, 'Fixed income': 30, 'Gold': 10, 'Cash / liquid': 10},
        'Growth': {'Equity': 70, 'Fixed income': 15, 'Gold': 10, 'Cash / liquid': 5},
    }.get(profile, {'Equity': 50, 'Fixed income': 30, 'Gold': 10, 'Cash / liquid': 10})


def save_profile(user_id, objective, horizon_years, risk_comfort, loss_reaction, emergency_months, monthly_investment):
    profile, score = calculate_profile(objective, horizon_years, risk_comfort, loss_reaction)
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO investor_profiles
                (user_id, objective, horizon_years, risk_comfort, loss_reaction, emergency_months, monthly_investment, profile, score, updated_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,CURRENT_TIMESTAMP)
                ON CONFLICT (user_id) DO UPDATE SET
                    objective=EXCLUDED.objective,
                    horizon_years=EXCLUDED.horizon_years,
                    risk_comfort=EXCLUDED.risk_comfort,
                    loss_reaction=EXCLUDED.loss_reaction,
                    emergency_months=EXCLUDED.emergency_months,
                    monthly_investment=EXCLUDED.monthly_investment,
                    profile=EXCLUDED.profile,
                    score=EXCLUDED.score,
                    updated_at=CURRENT_TIMESTAMP
            """, (user_id, objective, int(horizon_years), risk_comfort, loss_reaction,
                  _num(emergency_months), _num(monthly_investment), profile, score))
        conn.commit()
    finally:
        conn.close()
    return profile


def get_profile(user_id):
    ensure_investment_schema()
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT objective,horizon_years,risk_comfort,loss_reaction,emergency_months,monthly_investment,profile,score FROM investor_profiles WHERE user_id=%s", (user_id,))
            r = cur.fetchone()
    finally:
        conn.close()
    if not r:
        return None
    return {'objective':r[0], 'horizon_years':r[1], 'risk_comfort':r[2], 'loss_reaction':r[3],
            'emergency_months':float(r[4] or 0), 'monthly_investment':float(r[5] or 0), 'profile':r[6], 'score':r[7]}


def add_investment(user_id, name, symbol, asset_type, sector, quantity, average_cost, current_price, currency, notes=''):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""INSERT INTO investments
                (user_id,name,symbol,asset_type,sector,quantity,average_cost,current_price,currency,notes)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (user_id,name,symbol or None,asset_type,sector or None,_num(quantity),_num(average_cost),_num(current_price),currency,notes or None))
        conn.commit()
    finally:
        conn.close()


def update_investment_price(user_id, investment_id, current_price, change_pct=None, market_sync=False, resolved_symbol=None):
    conn=get_connection()
    try:
        with conn.cursor() as cur:
            if market_sync:
                cur.execute("""UPDATE investments SET current_price=%s, market_change_pct=%s,
                            market_price_updated_at=CURRENT_TIMESTAMP,
                            symbol=COALESCE(NULLIF(%s,''),symbol), updated_at=CURRENT_TIMESTAMP
                            WHERE id=%s AND user_id=%s""",
                            (_num(current_price), change_pct, (resolved_symbol or '').upper(), investment_id, user_id))
            else:
                cur.execute("UPDATE investments SET current_price=%s,updated_at=CURRENT_TIMESTAMP WHERE id=%s AND user_id=%s", (_num(current_price),investment_id,user_id))
        conn.commit()
    finally: conn.close()


def delete_investment(user_id, investment_id):
    conn=get_connection()
    try:
        with conn.cursor() as cur: cur.execute("DELETE FROM investments WHERE id=%s AND user_id=%s", (investment_id,user_id))
        conn.commit()
    finally: conn.close()


def get_investments(user_id):
    ensure_investment_schema()
    conn=get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""SELECT id,name,symbol,asset_type,sector,quantity,average_cost,current_price,currency,notes,
                           market_change_pct,market_price_updated_at
                           FROM investments WHERE user_id=%s ORDER BY current_price*quantity DESC,id DESC""", (user_id,))
            rows=cur.fetchall()
    finally: conn.close()
    out=[]
    for r in rows:
        qty=float(r[5] or 0); cost=float(r[6] or 0); price=float(r[7] or 0)
        invested=qty*cost; value=qty*price; gain=value-invested
        out.append({'id':r[0],'name':r[1],'symbol':r[2] or '','asset_type':r[3],'sector':r[4] or 'Unspecified','quantity':qty,
                    'average_cost':cost,'current_price':price,'currency':r[8] or 'INR','notes':r[9] or '',
                    'market_change_pct':float(r[10]) if r[10] is not None else None,
                    'market_price_updated_at':str(r[11]) if r[11] else None,
                    'invested':invested,'value':value,'gain':gain,'return_pct':(gain/invested*100 if invested else 0)})
    return out


def add_watchlist(user_id,name,symbol,asset_type,note=''):
    conn=get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO investment_watchlist (user_id,name,symbol,asset_type,note) VALUES (%s,%s,%s,%s,%s)", (user_id,name,symbol or None,asset_type,note or None))
        conn.commit()
    finally: conn.close()


def delete_watchlist(user_id,item_id):
    conn=get_connection()
    try:
        with conn.cursor() as cur: cur.execute("DELETE FROM investment_watchlist WHERE id=%s AND user_id=%s", (item_id,user_id))
        conn.commit()
    finally: conn.close()


def get_watchlist(user_id):
    ensure_investment_schema(); conn=get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id,name,symbol,asset_type,note FROM investment_watchlist WHERE user_id=%s ORDER BY id DESC",(user_id,)); rows=cur.fetchall()
    finally: conn.close()
    return [{'id':r[0],'name':r[1],'symbol':r[2] or '','asset_type':r[3],'note':r[4] or ''} for r in rows]


def portfolio_summary(user_id):
    holdings=get_investments(user_id)
    invested=sum(x['invested'] for x in holdings); value=sum(x['value'] for x in holdings); gain=value-invested
    by_asset=defaultdict(float); by_sector=defaultdict(float)
    for x in holdings:
        by_asset[x['asset_type']]+=x['value']; by_sector[x['sector']]+=x['value']
    allocations={k:(v/value*100 if value else 0) for k,v in by_asset.items()}
    sectors={k:(v/value*100 if value else 0) for k,v in by_sector.items()}
    warnings=[]
    biggest=max(holdings,key=lambda x:x['value']) if holdings else None
    biggest_pct=(biggest['value']/value*100) if biggest and value else 0
    if value:
        if allocations and max(allocations.values()) >= 75:
            k=max(allocations,key=allocations.get); warnings.append(f"{allocations[k]:.0f}% of your tracked portfolio is in {k}. High concentration can amplify losses as well as gains.")
        if sectors and max(sectors.values()) >= 50 and max(sectors,key=sectors.get) != 'Unspecified':
            k=max(sectors,key=sectors.get); warnings.append(f"{sectors[k]:.0f}% of your tracked portfolio is in the {k} sector.")
        if biggest and biggest_pct >= 35:
            warnings.append(f"{biggest['name']} is {biggest_pct:.0f}% of the tracked portfolio.")
    today_change=sum((x['value'] * (x.get('market_change_pct') or 0) / (100 + (x.get('market_change_pct') or 0))) if (x.get('market_change_pct') is not None and (100 + x.get('market_change_pct')) != 0) else 0 for x in holdings)
    today_pct=(today_change/(value-today_change)*100) if value and (value-today_change) else 0
    return {'holdings':holdings,'invested':invested,'value':value,'gain':gain,'return_pct':(gain/invested*100 if invested else 0),
            'allocations':dict(allocations),'sectors':dict(sectors),'warnings':warnings,
            'biggest_holding':biggest,'biggest_pct':biggest_pct,'today_change':today_change,'today_pct':today_pct}


def portfolio_health(portfolio, cashflow=None):
    """Explainable educational portfolio-health score. No security recommendations."""
    holdings=portfolio.get('holdings') or []
    if not holdings:
        return {'score':None,'label_key':'health_not_enough','signal_keys':[]}
    score=100; signals=[]
    biggest=float(portfolio.get('biggest_pct') or 0)
    if biggest >= 60:
        score-=30; signals.append('health_signal_very_high_concentration')
    elif biggest >= 40:
        score-=20; signals.append('health_signal_high_concentration')
    elif biggest >= 25:
        score-=8; signals.append('health_signal_moderate_concentration')
    else:
        signals.append('health_signal_controlled_concentration')
    asset_count=len([v for v in (portfolio.get('allocations') or {}).values() if v > 1])
    if len(holdings) == 1:
        score-=20; signals.append('health_signal_one_holding')
    elif len(holdings) < 4:
        score-=10; signals.append('health_signal_limited_breadth')
    else:
        signals.append('health_signal_multiple_holdings')
    if asset_count <= 1 and len(holdings) >= 2:
        score-=10; signals.append('health_signal_one_asset_class')
    cf=cashflow or {}
    if cf.get('emergency_months',0) < 3:
        score-=12; signals.append('health_signal_low_emergency')
    elif cf.get('emergency_months',0) >= 6:
        signals.append('health_signal_strong_emergency')
    score=max(0,min(100,score))
    label='health_strong' if score>=80 else 'health_balanced' if score>=65 else 'health_attention' if score>=45 else 'health_concentration_risk'
    return {'score':score,'label_key':label,'signal_keys':signals[:4]}


def financial_investment_context(user_id, profile=None):
    report=get_report_totals(user_id)
    income=float(report.get('total_income',0) or 0); expense=float(report.get('total_expense',0) or 0)
    surplus=income-expense
    p=profile or get_profile(user_id)
    monthly_target=(p or {}).get('monthly_investment',0)
    reserve_months=(p or {}).get('emergency_months',0)
    messages=[]
    if surplus <= 0:
        messages.append('Your tracked expenses currently meet or exceed tracked income. Consider stabilising cash flow before increasing investment contributions.')
    elif monthly_target and monthly_target > surplus:
        messages.append('Your chosen monthly investment amount is higher than your tracked surplus. Review the amount before committing it.')
    if p and reserve_months < 3:
        messages.append('Your entered emergency-fund coverage is below 3 months. Building liquidity may deserve attention before taking more market risk.')
    return {'income':income,'expense':expense,'surplus':surplus,'monthly_target':monthly_target,'emergency_months':reserve_months,'messages':messages}


EXPLORER = [
    {'category':'Broad-market equity','examples':'Nifty 50 / Sensex index funds or ETFs','risk':'High','horizon':'5+ years','role':'Diversified exposure to large Indian companies.'},
    {'category':'Broader equity','examples':'Nifty 500 / total-market style index funds','risk':'High','horizon':'7+ years','role':'Wider equity diversification across market segments.'},
    {'category':'Government fixed income','examples':'Treasury bills / government securities','risk':'Low–Moderate','horizon':'Months to years','role':'Lower-volatility fixed-income exposure; values can still move with interest rates.'},
    {'category':'Bank deposits','examples':'FD / RD from regulated banks','risk':'Low','horizon':'Defined tenure','role':'Capital stability and predictable interest, subject to institution/tenure terms.'},
    {'category':'Gold','examples':'Gold ETF / eligible regulated gold products','risk':'Moderate','horizon':'3+ years','role':'Diversifier; prices can be volatile and do not generate business cash flows.'},
    {'category':'Individual equities','examples':'Listed companies across banking, IT, consumer, industrial and other sectors','risk':'High','horizon':'5+ years','role':'Company-specific exposure requiring deeper research and diversification.'},
]
