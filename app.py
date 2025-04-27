from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import sqlite3
import json
import os
from add_sample_data import generate_grocery_products
from sqlalchemy import func

app = Flask(__name__)
app.secret_key = "wms_secret_key"  # 플래시 메시지를 위한 시크릿 키 추가

# SQLite 데이터베이스 설정 (MySQL 대신 사용)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///wms.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# 제품 모델 정의
class Product(db.Model):
    __tablename__ = 'products'
    product_id = db.Column(db.String(20), primary_key=True)
    product_name = db.Column(db.String(100), nullable=False)
    product_name_en = db.Column(db.String(100))
    category = db.Column(db.String(50), nullable=False)
    purchase_price = db.Column(db.Numeric(10,2), nullable=False)
    selling_price = db.Column(db.Numeric(10,2), nullable=False)
    standard_quantity = db.Column(db.Integer, nullable=False)
    current_stock = db.Column(db.Integer, nullable=False)
    minimum_stock = db.Column(db.Integer, nullable=False)
    individual_weight = db.Column(db.Numeric(10,2))  # 개별 무게
    weight_unit = db.Column(db.String(10), nullable=False)
    box_quantity = db.Column(db.Integer)  # 박스단위 수량
    location = db.Column(db.String(50))  # 제품 위치
    box_qr = db.Column(db.String(100))   # 박스 QR 코드
    pallet_qr = db.Column(db.String(100)) # 팔렛 QR 코드
    sort_order = db.Column(db.Integer, default=0)  # 정렬 번호
    size = db.Column(db.String(50))  # 크기 정보
    storage_location = db.Column(db.String(100))  # 보관 위치
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=True)  # 담당자 ID
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 관계 설정
    employee = db.relationship('Employee', backref='products')

# 입출고 기록 모델 정의
class InventoryTransaction(db.Model):
    __tablename__ = 'inventory_transactions'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    product_id = db.Column(db.String(20), db.ForeignKey('products.product_id'))
    transaction_date = db.Column(db.DateTime, default=datetime.now)
    transaction_type = db.Column(db.String(10), nullable=False)  # IN or OUT
    quantity = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    product = db.relationship('Product', backref='transactions')

# 고객 모델 정의
class Customer(db.Model):
    __tablename__ = 'customers'
    customer_id = db.Column(db.String(20), primary_key=True)
    company_name = db.Column(db.String(100), nullable=False)
    contact_name = db.Column(db.String(50))
    contact_phone = db.Column(db.String(20))
    address = db.Column(db.String(200))
    email = db.Column(db.String(100))
    note = db.Column(db.Text)
    status = db.Column(db.String(20), default='활성고객')  # 활성고객, 휴면고객, 잠재고객
    payment_term = db.Column(db.String(50))  # 결제 조건
    register_date = db.Column(db.DateTime, default=datetime.now)  # 등록일
    last_order_date = db.Column(db.DateTime)  # 마지막 주문일
    total_purchase_amount = db.Column(db.Numeric(15, 2), default=0)  # 총 구매 금액
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=True)  # 담당자 ID
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 관계 추가
    employee = db.relationship('Employee', backref='customers')

# 직원 모델 정의
class Employee(db.Model):
    __tablename__ = 'employees'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    employee_id = db.Column(db.String(20))  # 직원 고유 ID 필드 추가
    name = db.Column(db.String(50), nullable=False)
    department = db.Column(db.String(50))
    position = db.Column(db.String(50))
    phone = db.Column(db.String(20))  # contact_number에서 phone으로 변경
    email = db.Column(db.String(100))
    hire_date = db.Column(db.Date, default=datetime.now().date())
    status = db.Column(db.String(20), default='재직중')  # 재직중, 휴직중, 퇴사
    address = db.Column(db.String(200))  # 주소 추가
    notes = db.Column(db.Text)  # note에서 notes로 변경
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

# 주문 모델 정의
class Order(db.Model):
    __tablename__ = 'orders'
    order_id = db.Column(db.String(20), primary_key=True)
    customer_id = db.Column(db.String(20), db.ForeignKey('customers.customer_id'), nullable=False)
    order_date = db.Column(db.DateTime, default=datetime.now)
    delivery_date = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='준비중')  # 준비중, 배송중, 완료, 취소
    total_amount = db.Column(db.Numeric(15, 2), default=0)
    note = db.Column(db.Text)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 관계 설정
    customer = db.relationship('Customer', backref='orders')
    employee = db.relationship('Employee', backref='orders')
    order_items = db.relationship('OrderItem', backref='order', cascade='all, delete-orphan')

# 주문 항목 모델 정의
class OrderItem(db.Model):
    __tablename__ = 'order_items'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    order_id = db.Column(db.String(20), db.ForeignKey('orders.order_id'), nullable=False)
    product_id = db.Column(db.String(20), db.ForeignKey('products.product_id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    subtotal = db.Column(db.Numeric(15, 2), nullable=False)
    
    # 관계 설정
    product = db.relationship('Product')

# 샘플 데이터 추가 함수
def add_sample_data():
    """샘플 데이터 추가"""
    try:
        # 기존 데이터 삭제
        print("기존 데이터를 삭제하고 새로운 샘플 데이터를 추가합니다.")
        db.session.query(OrderItem).delete()
        db.session.query(Order).delete()
        db.session.query(Product).delete()
        db.session.query(Customer).delete()
        db.session.query(Employee).delete()
        db.session.commit()
        
        # 직원 추가
        employees = [
            Employee(name="김관리", department="관리부", position="부장", phone="010-1234-5678", hire_date=datetime.strptime("2020-01-15", "%Y-%m-%d").date()),
            Employee(name="이영업", department="영업부", position="과장", phone="010-2345-6789", hire_date=datetime.strptime("2021-03-10", "%Y-%m-%d").date()),
            Employee(name="박물류", department="물류부", position="대리", phone="010-3456-7890", hire_date=datetime.strptime("2022-05-20", "%Y-%m-%d").date())
        ]
        
        db.session.add_all(employees)
        db.session.commit()
        print("직원 샘플 데이터가 추가되었습니다.")
        
        # 고객(업체) 10개 추가
        customers = [
            Customer(customer_id="C001", company_name="가나상사", contact_name="강가나", contact_phone="010-1111-2222", email="gana@example.com", address="서울시 강남구", employee_id=1),
            Customer(customer_id="C002", company_name="다라물산", contact_name="이다라", contact_phone="010-3333-4444", email="dara@example.com", address="서울시 서초구", employee_id=2),
            Customer(customer_id="C003", company_name="마바식품", contact_name="정마바", contact_phone="010-5555-6666", email="maba@example.com", address="경기도 성남시", employee_id=3),
            Customer(customer_id="C004", company_name="테크놀로지스", contact_name="김기술", contact_phone="010-7777-8888", email="tech@example.com", address="경기도 판교", employee_id=1),
            Customer(customer_id="C005", company_name="글로벌트레이딩", contact_name="박국제", contact_phone="010-9999-0000", email="global@example.com", address="인천시 송도", employee_id=2),
            Customer(customer_id="C006", company_name="푸드마스터", contact_name="최음식", contact_phone="010-1212-3434", email="food@example.com", address="서울시 마포구", employee_id=3),
            Customer(customer_id="C007", company_name="이지로지스", contact_name="정물류", contact_phone="010-5656-7878", email="easy@example.com", address="경기도 안양시", employee_id=1),
            Customer(customer_id="C008", company_name="뉴트렌드", contact_name="이유행", contact_phone="010-9090-1010", email="trend@example.com", address="서울시 강북구", employee_id=2),
            Customer(customer_id="C009", company_name="하이테크", contact_name="박첨단", contact_phone="010-1313-2424", email="hitech@example.com", address="대전시 유성구", employee_id=3),
            Customer(customer_id="C010", company_name="베스트초이스", contact_name="김선택", contact_phone="010-3535-4646", email="best@example.com", address="부산시 해운대구", employee_id=1)
        ]
        
        db.session.add_all(customers)
        db.session.commit()
        print("10개의 고객 샘플 데이터가 추가되었습니다.")
        
        # 제품 카테고리 정의
        categories = ['과일', '채소', '육류', '유제품', '곡물']
        
        # 제품 100개 추가
        products = []
        for i in range(1, 101):
            category = categories[i % len(categories)]
            product_id = f"P{i:03d}"
            
            # 카테고리별 제품명 생성
            if category == '과일':
                product_name = f"과일상품{i}"
                product_name_en = f"Fruit{i}"
                weight_unit = "kg"
                storage_location = "냉장"
            elif category == '채소':
                product_name = f"채소상품{i}"
                product_name_en = f"Vegetable{i}"
                weight_unit = "kg"
                storage_location = "상온"
            elif category == '육류':
                product_name = f"육류상품{i}"
                product_name_en = f"Meat{i}"
                weight_unit = "kg"
                storage_location = "냉동"
            elif category == '유제품':
                product_name = f"유제품{i}"
                product_name_en = f"Dairy{i}"
                weight_unit = "g"
                storage_location = "냉장"
            else:  # 곡물
                product_name = f"곡물상품{i}"
                product_name_en = f"Grain{i}"
                weight_unit = "kg"
                storage_location = "상온"
            
            # 가격 생성
            purchase_price = 5000 + (i * 100)
            selling_price = int(purchase_price * 1.3)
            
            # 재고 관련 수량 설정
            standard_quantity = 50 + (i % 50)
            current_stock = 30 + (i % 70)
            minimum_stock = 10 + (i % 10)
            
            # 무게 관련 설정
            individual_weight = round(0.1 + (i / 100), 2)
            
            # 박스당 수량
            box_quantity = 10 + (i % 40)
            
            # 위치 및 QR 코드
            location = f"{chr(65 + (i % 5))}-{1 + (i % 5)}"
            box_qr = f"BOX-{product_id}-{1000 + i}"
            pallet_qr = f"PLT-{product_id}-{2000 + i}"
            
            # 담당자 ID 설정
            employee_id = 1 + (i % 3)
            
            # 새로운 필드 설정
            sort_order = i  # 정렬 번호는 제품 순서대로
            
            # 크기 정보 설정
            sizes = ["소", "중", "대"]
            size = sizes[i % len(sizes)]
            
            product = Product(
                product_id=product_id,
                product_name=product_name,
                product_name_en=product_name_en,
                category=category,
                purchase_price=purchase_price,
                selling_price=selling_price,
                standard_quantity=standard_quantity,
                current_stock=current_stock,
                minimum_stock=minimum_stock,
                individual_weight=individual_weight,
                weight_unit=weight_unit,
                box_quantity=box_quantity,
                location=location,
                box_qr=box_qr,
                pallet_qr=pallet_qr,
                sort_order=sort_order,
                size=size,
                storage_location=storage_location,
                employee_id=employee_id,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            products.append(product)
        
        db.session.add_all(products)
        db.session.commit()
        print(f"100개의 제품 샘플 데이터가 추가되었습니다.")
        
        # 샘플 주문 10개 추가
        orders = []
        today = datetime.now().date()
        
        for i in range(1, 11):
            # 주문 ID 생성
            order_id = f"ORD-{today.strftime('%Y%m%d')}-{i:03d}"
            
            # 고객 ID 선택
            customer_id = f"C{i:03d}" if i <= 10 else f"C{(i % 10) + 1:03d}"
            
            # 주문 날짜 설정 (최근 30일 내)
            days_ago = i * 3  # 3일 간격으로 주문 생성
            order_date = today - timedelta(days=days_ago)
            
            # 배송 예정일 설정 (주문일로부터 3-7일 후)
            delivery_date = order_date + timedelta(days=3 + (i % 5))
            
            # 주문 상태 설정
            statuses = ['준비중', '배송중', '완료', '취소']
            status_idx = i % 4
            status = statuses[status_idx]
            
            # 담당 직원 설정
            employee_id = 1 + (i % 3)
            
            # 메모 추가
            notes = f"샘플 주문 {i}입니다. 특이사항: {'없음' if i % 2 == 0 else '배송 시 연락 요망'}"
            
            # 총 금액은 주문 항목 추가 후 계산
            order = Order(
                order_id=order_id,
                customer_id=customer_id,
                order_date=order_date,
                delivery_date=delivery_date,
                status=status,
                employee_id=employee_id,
                note=notes,
                total_amount=0
            )
            
            orders.append(order)
        
        db.session.add_all(orders)
        db.session.commit()
        
        # 주문 항목 추가
        order_items = []
        
        for i, order in enumerate(orders, 1):
            # 각 주문마다 3-5개의 제품 추가
            num_products = 3 + (i % 3)
            total_amount = 0
            
            for j in range(num_products):
                # 제품 ID 선택 (중복 없이)
                product_idx = (i * 10 + j) % 100
                product_id = f"P{product_idx + 1:03d}"
                
                # 제품 정보 조회
                product = Product.query.get(product_id)
                
                # 수량과 단가 설정
                quantity = 1 + (j * 2)
                unit_price = float(product.selling_price)
                subtotal = float(quantity * unit_price)
                
                order_item = OrderItem(
                    order_id=order.order_id,
                    product_id=product_id,
                    quantity=quantity,
                    unit_price=unit_price,
                    subtotal=subtotal
                )
                
                order_items.append(order_item)
                total_amount += subtotal
            
            # 주문 총액 업데이트
            order.total_amount = total_amount
        
        db.session.add_all(order_items)
        db.session.commit()
        print("10개의 주문 샘플 데이터가 추가되었습니다.")

    except Exception as e:
        db.session.rollback()
        print(f"샘플 데이터 추가 중 오류 발생: {e}")

# 설정 파일 경로
CONFIG_FILE = 'config.json'

# 설정 파일 로드
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        'company_name': 'WMS 시스템',
        'currency': 'USD',
        'date_format': 'YYYY-MM-DD'
    }

# 설정 파일 저장
def save_config(config):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=4)

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    config = load_config()
    
    if request.method == 'POST':
        config['company_name'] = request.form.get('company_name', '')
        config['currency'] = request.form.get('currency', 'USD')
        config['date_format'] = request.form.get('date_format', 'YYYY-MM-DD')
        
        save_config(config)
        flash('설정이 저장되었습니다.', 'success')
        return redirect(url_for('settings'))
    
    return render_template('settings.html', config=config)

@app.route('/')
def index():
    # 검색 쿼리 처리
    search_query = request.args.get('search', '')
    
    if search_query:
        search_term = f"%{search_query}%"
        products = Product.query.filter(
            db.or_(
                Product.product_id.like(search_term),
                Product.product_name.like(search_term),
                Product.product_name_en.like(search_term),
                Product.category.like(search_term),
                Product.location.like(search_term)
            )
        ).all()
    else:
        products = Product.query.all()
    
    return render_template('index.html', products=products, search_query=search_query)

@app.route('/customers')
def customers():
    # 검색 쿼리 처리
    search_query = request.args.get('search', '')
    
    if search_query:
        search_term = f"%{search_query}%"
        customers_list = Customer.query.filter(
            db.or_(
                Customer.customer_id.like(search_term),
                Customer.company_name.like(search_term),
                Customer.contact_name.like(search_term),
                Customer.contact_phone.like(search_term),
                Customer.email.like(search_term),
                Customer.address.like(search_term)
            )
        ).all()
    else:
        customers_list = Customer.query.all()
    
    return render_template('customers.html', customers=customers_list, search_query=search_query)

@app.route('/dashboard')
def dashboard():
    # 최근 1년간의 베스트 제품 데이터 가져오기
    one_year_ago = datetime.now() - timedelta(days=365)
    best_products = db.session.query(
        Product.product_name,
        Product.category,
        func.sum(OrderItem.quantity).label('total_quantity'),
        func.sum(OrderItem.subtotal).label('total_revenue')
    ).join(OrderItem, Product.product_id == OrderItem.product_id)\
     .join(Order, OrderItem.order_id == Order.order_id)\
     .filter(Order.order_date >= one_year_ago)\
     .group_by(Product.product_id)\
     .order_by(func.sum(OrderItem.quantity).desc())\
     .limit(10)\
     .all()

    # 기존 대시보드 데이터
    total_products = Product.query.count()
    total_customers = Customer.query.count()
    total_orders = Order.query.count()
    total_employees = Employee.query.count()
    
    # 최근 주문 목록
    recent_orders = Order.query.order_by(Order.order_date.desc()).limit(5).all()
    
    return render_template('dashboard.html', 
                         total_products=total_products,
                         total_customers=total_customers,
                         total_orders=total_orders,
                         total_employees=total_employees,
                         recent_orders=recent_orders,
                         best_products=best_products)

@app.route('/add_product', methods=['GET', 'POST'])
def add_product():
    if request.method == 'POST':
        # 폼에서 제출된 데이터 가져오기
        product_id = request.form.get('product_id')
        product_name = request.form.get('product_name')
        product_name_en = request.form.get('product_name_en')
        category = request.form.get('category')
        # 새 카테고리 입력이 있는 경우 해당 값을 사용
        if category == 'new':
            category = request.form.get('new_category')
        purchase_price = request.form.get('purchase_price')
        selling_price = request.form.get('selling_price')
        standard_quantity = request.form.get('standard_quantity')
        current_stock = request.form.get('current_stock')
        minimum_stock = request.form.get('minimum_stock')
        weight_unit = request.form.get('weight_unit')
        individual_weight = request.form.get('individual_weight')  # 개별 무게 정보 가져오기
        box_quantity = request.form.get('box_quantity')  # 박스단위 수량 정보 가져오기
        location = request.form.get('location')      # 위치 정보 가져오기
        box_qr = request.form.get('box_qr')          # 박스 QR 정보 가져오기
        pallet_qr = request.form.get('pallet_qr')    # 팔렛 QR 정보 가져오기
        
        # 새로 추가된 필드 정보 가져오기
        sort_order = request.form.get('sort_order', 0)
        size = request.form.get('size', '')
        storage_location = request.form.get('storage_location', '')
        
        # 담당자 ID 처리
        employee_id_raw = request.form.get('employee_id')
        employee_id = None
        if employee_id_raw and employee_id_raw.strip():
            employee_id = int(employee_id_raw)
        
        # 제품 ID가 이미 존재하는지 확인
        existing_product = Product.query.filter_by(product_id=product_id).first()
        if existing_product:
            flash('이미 존재하는 제품 ID입니다.', 'danger')
            return redirect(url_for('add_product'))
        
        # 새 제품 생성
        new_product = Product(
            product_id=product_id,
            product_name=product_name,
            product_name_en=product_name_en,
            category=category,
            purchase_price=purchase_price,
            selling_price=selling_price,
            standard_quantity=standard_quantity,
            current_stock=current_stock,
            minimum_stock=minimum_stock,
            weight_unit=weight_unit,
            individual_weight=individual_weight,  # 개별 무게 추가
            box_quantity=box_quantity,  # 박스단위 수량 추가
            location=location,                # 위치 정보 추가
            box_qr=box_qr,                    # 박스 QR 정보 추가
            pallet_qr=pallet_qr,              # 팔렛 QR 정보 추가
            sort_order=sort_order,            # 정렬 번호 추가
            size=size,                        # 크기 정보 추가
            storage_location=storage_location,  # 보관 위치 추가
            employee_id=employee_id           # 담당자 ID 추가
        )
        
        # 데이터베이스에 추가
        try:
            db.session.add(new_product)
            db.session.commit()
            flash('제품이 성공적으로 추가되었습니다!', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            db.session.rollback()
            flash(f'제품 추가 중 오류가 발생했습니다: {str(e)}', 'danger')
            return redirect(url_for('add_product'))
    
    # GET 요청 - 추가 페이지 표시
    # 카테고리 목록 가져오기
    categories = db.session.query(Product.category).distinct().all()
    categories = [category[0] for category in categories]
    
    # 직원 목록 가져오기
    employees = Employee.query.order_by(Employee.name).all()
    
    return render_template('add_product.html', categories=categories, employees=employees)

@app.route('/add_customer', methods=['GET', 'POST'])
def add_customer():
    if request.method == 'POST':
        # 폼에서 제출된 데이터 가져오기
        customer_id = request.form.get('customer_id')
        company_name = request.form.get('company_name')
        contact_name = request.form.get('contact_name')
        contact_phone = request.form.get('contact_phone')
        email = request.form.get('email')
        address = request.form.get('address')
        note = request.form.get('note')
        
        # 고객 ID가 이미 존재하는지 확인
        existing_customer = Customer.query.filter_by(customer_id=customer_id).first()
        if existing_customer:
            flash('이미 존재하는 고객 ID입니다.', 'danger')
            return redirect(url_for('add_customer'))
        
        # 새 고객 생성
        new_customer = Customer(
            customer_id=customer_id,
            company_name=company_name,
            contact_name=contact_name,
            contact_phone=contact_phone,
            email=email,
            address=address,
            note=note
        )
        
        # 데이터베이스에 추가
        try:
            db.session.add(new_customer)
            db.session.commit()
            flash('고객이 성공적으로 추가되었습니다!', 'success')
            return redirect(url_for('customers'))
        except Exception as e:
            db.session.rollback()
            flash(f'고객 추가 중 오류가 발생했습니다: {str(e)}', 'danger')
            return redirect(url_for('add_customer'))
    
    # GET 요청 - 고객 추가 페이지 표시
    # 직원 목록 가져오기
    employees = Employee.query.order_by(Employee.name).all()
    
    return render_template('add_customer.html', employees=employees)

@app.route('/edit_product/<product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    product = Product.query.filter_by(product_id=product_id).first_or_404()
    
    if request.method == 'POST':
        # 폼에서 제출된 데이터 가져오기
        product.product_name = request.form.get('product_name')
        product.product_name_en = request.form.get('product_name_en')
        
        category = request.form.get('category')
        # 새 카테고리 입력이 있는 경우 해당 값을 사용
        if category == 'new':
            product.category = request.form.get('new_category')
        else:
            product.category = category
            
        product.purchase_price = request.form.get('purchase_price')
        product.selling_price = request.form.get('selling_price')
        product.standard_quantity = request.form.get('standard_quantity')
        product.current_stock = request.form.get('current_stock')
        product.minimum_stock = request.form.get('minimum_stock')
        product.weight_unit = request.form.get('weight_unit')
        product.individual_weight = request.form.get('individual_weight')  # 개별 무게 업데이트
        product.box_quantity = request.form.get('box_quantity')  # 박스단위 수량 업데이트
        product.location = request.form.get('location')        # 위치 정보 업데이트
        product.box_qr = request.form.get('box_qr')            # 박스 QR 정보 업데이트
        product.pallet_qr = request.form.get('pallet_qr')      # 팔렛 QR 정보 업데이트
        
        # 새로 추가된 필드 정보 업데이트
        product.sort_order = request.form.get('sort_order', 0)
        product.size = request.form.get('size', '')
        product.storage_location = request.form.get('storage_location', '')
        
        # 담당자 ID 처리 (빈 문자열이나 None일 경우 None으로 설정)
        employee_id = request.form.get('employee_id')
        if employee_id and employee_id.strip():
            product.employee_id = int(employee_id)
        else:
            product.employee_id = None
        
        # 데이터베이스에 변경사항 저장
        try:
            db.session.commit()
            flash('제품이 성공적으로 업데이트되었습니다!', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            db.session.rollback()
            flash(f'제품 업데이트 중 오류가 발생했습니다: {str(e)}', 'danger')
            return redirect(url_for('edit_product', product_id=product_id))
    
    # GET 요청 - 편집 페이지 표시
    # 카테고리 목록 가져오기
    categories = db.session.query(Product.category).distinct().all()
    categories = [category[0] for category in categories]
    
    # 직원 목록 가져오기
    employees = Employee.query.order_by(Employee.name).all()
    
    return render_template('edit_product.html', product=product, categories=categories, employees=employees)

@app.route('/edit_customer/<customer_id>', methods=['GET', 'POST'])
def edit_customer(customer_id):
    customer = Customer.query.get_or_404(customer_id)
    
    if request.method == 'POST':
        try:
            customer.company_name = request.form['company_name']
            customer.contact_name = request.form['contact_name']
            customer.contact_phone = request.form['contact_phone']
            customer.address = request.form['address']
            customer.email = request.form['email']
            customer.status = request.form['status']
            customer.payment_term = request.form['payment_term']
            customer.note = request.form.get('note', '')  # note 필드가 폼에 없을 경우 빈 문자열 사용
            customer.employee_id = request.form.get('employee_id')  # 직원 ID 처리
            
            db.session.commit()
            flash('고객 정보가 성공적으로 수정되었습니다.', 'success')
            return redirect(url_for('customers'))
        except Exception as e:
            db.session.rollback()
            flash(f'고객 정보 수정 중 오류가 발생했습니다: {str(e)}', 'danger')
            return redirect(url_for('edit_customer', customer_id=customer_id))
    
    # GET 요청 - 편집 페이지 표시
    # 직원 목록 가져오기
    employees = Employee.query.order_by(Employee.name).all()
    
    return render_template('edit_customer.html', customer=customer, employees=employees)

@app.route('/api/delete_products', methods=['POST'])
def delete_products():
    try:
        # 요청에서 제품 ID 목록 가져오기
        data = request.json
        product_ids = data.get('product_ids', [])
        
        if not product_ids:
            return jsonify({'success': False, 'message': '삭제할 제품이 선택되지 않았습니다.'}), 400
        
        # 각 제품에 대해 연결된 트랜잭션 먼저 삭제
        for product_id in product_ids:
            # 제품이 존재하는지 확인
            product = Product.query.get(product_id)
            if product:
                # 연결된 트랜잭션 삭제
                InventoryTransaction.query.filter_by(product_id=product_id).delete()
                # 제품 삭제
                db.session.delete(product)
        
        # 변경사항 커밋
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'{len(product_ids)}개의 제품이 성공적으로 삭제되었습니다.',
            'deleted_count': len(product_ids)
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'제품 삭제 중 오류가 발생했습니다: {str(e)}'
        }), 500

@app.route('/api/delete_customers', methods=['POST'])
def delete_customers():
    try:
        # 요청에서 고객 ID 목록 가져오기
        data = request.json
        customer_ids = data.get('customer_ids', [])
        
        if not customer_ids:
            return jsonify({'success': False, 'message': '삭제할 고객이 선택되지 않았습니다.'}), 400
        
        deleted_count = 0
        # 각 고객 삭제
        for customer_id in customer_ids:
            # 고객이 존재하는지 확인
            customer = Customer.query.get(customer_id)
            if customer:
                # 고객 삭제
                db.session.delete(customer)
                deleted_count += 1
        
        # 변경사항 커밋
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'{deleted_count}명의 고객이 성공적으로 삭제되었습니다.',
            'deleted_count': deleted_count
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'고객 삭제 중 오류가 발생했습니다: {str(e)}'
        }), 500

# 직원 관리 라우트
@app.route('/employees')
def employees():
    # 검색 쿼리 처리
    search_query = request.args.get('search', '')
    
    if search_query:
        search_term = f"%{search_query}%"
        employees_list = Employee.query.filter(
            db.or_(
                Employee.name.like(search_term),
                Employee.phone.like(search_term),
                Employee.department.like(search_term),
                Employee.position.like(search_term),
                Employee.email.like(search_term),
                Employee.hire_date.like(search_term)
            )
        ).order_by(Employee.hire_date.desc()).all()
    else:
        employees_list = Employee.query.order_by(Employee.hire_date.desc()).all()
    
    return render_template('employees.html', employees=employees_list, search_query=search_query)

@app.route('/add_employee', methods=['GET', 'POST'])
def add_employee():
    if request.method == 'POST':
        # 폼 데이터 가져오기
        employee_id = request.form.get('employee_id')  # employee_id 필드 추가
        name = request.form.get('name')
        department = request.form.get('department')
        position = request.form.get('position')
        phone = request.form.get('phone')  # 템플릿에서는 phone으로 사용됨
        email = request.form.get('email')
        hire_date_str = request.form.get('hire_date')
        note = request.form.get('notes')  # 템플릿은 notes로 되어있지만 모델은 notes로 저장
        status = request.form.get('status', '재직중')  # 상태 필드 추가
        address = request.form.get('address')  # 주소 필드 추가
        
        # employee_id 유효성 검사
        if not employee_id or employee_id.strip() == '':
            flash('직원 고유 ID는 필수입니다.', 'danger')
            return redirect(url_for('add_employee'))
            
        # 중복 employee_id 확인
        existing_employee = Employee.query.filter_by(employee_id=employee_id).first()
        if existing_employee:
            flash('이미 사용 중인 직원 고유 ID입니다.', 'danger')
            return redirect(url_for('add_employee'))
        
        # 전화번호 포맷팅
        if phone and phone.isdigit():
            # 숫자만 포함된 경우 하이픈 추가
            if len(phone) == 10:  # 예: 7142344901
                phone = f"{phone[:3]}-{phone[3:6]}-{phone[6:]}"
            elif len(phone) == 11:  # 예: 17142344901
                phone = f"{phone[:1]}-{phone[1:4]}-{phone[4:7]}-{phone[7:]}"
        
        # 입사일 처리
        try:
            # 설정에서 날짜 형식 가져오기
            config = load_config()
            date_format = config.get('date_format', 'YYYY-MM-DD')
            
            # 날짜 형식에 따라 처리
            if date_format == 'MM/DD/YYYY' and '/' in hire_date_str:
                # MM/DD/YYYY 형식을 YYYY-MM-DD로 변환
                month, day, year = hire_date_str.split('/')
                hire_date = datetime(int(year), int(month), int(day)).date()
            elif date_format == 'DD/MM/YYYY' and '/' in hire_date_str:
                # DD/MM/YYYY 형식을 YYYY-MM-DD로 변환
                day, month, year = hire_date_str.split('/')
                hire_date = datetime(int(year), int(month), int(day)).date()
            else:
                # 기본 YYYY-MM-DD 형식 처리
            hire_date = datetime.strptime(hire_date_str, '%Y-%m-%d').date() if hire_date_str else datetime.now().date()
        except ValueError as e:
            flash(f'유효하지 않은 날짜 형식입니다: {str(e)}', 'danger')
            return redirect(url_for('add_employee'))
        
        # 새 직원 생성
        new_employee = Employee(
            employee_id=employee_id,  # employee_id 필드 추가
            name=name,
            department=department,
            position=position,
            phone=phone,
            email=email,
            hire_date=hire_date,
            status=status,  # 상태 필드 추가
            address=address,  # 주소 필드 추가
            notes=note  # notes로 수정
        )
        
        try:
            db.session.add(new_employee)
            db.session.commit()
            flash('직원이 성공적으로 추가되었습니다.', 'success')
            return redirect(url_for('employees'))
        except Exception as e:
            db.session.rollback()
            flash(f'직원 추가 중 오류가 발생했습니다: {str(e)}', 'danger')
            return redirect(url_for('add_employee'))
    
    # 설정에서 날짜 형식 가져오기
    config = load_config()
    date_format = config.get('date_format', 'YYYY-MM-DD')
    
    # 클라이언트에서 사용할 날짜 형식 변환
    js_date_format = 'yyyy-mm-dd'  # 기본값
    if date_format == 'MM/DD/YYYY':
        js_date_format = 'mm/dd/yyyy'
    elif date_format == 'DD/MM/YYYY':
        js_date_format = 'dd/mm/yyyy'
    
    return render_template('add_employee.html', js_date_format=js_date_format)

@app.route('/edit_employee/<int:id>', methods=['GET', 'POST'])
def edit_employee(id):
    employee = Employee.query.get_or_404(id)
    
    if request.method == 'POST':
        # 폼 데이터 가져오기
        name = request.form.get('name')
        department = request.form.get('department')
        position = request.form.get('position')
        phone = request.form.get('phone')  # 템플릿에서는 phone으로 사용됨
        email = request.form.get('email')
        hire_date_str = request.form.get('hire_date')
        status = request.form.get('status')  # 상태 필드 추가
        address = request.form.get('address')  # 주소 필드 추가
        notes = request.form.get('notes')  # 템플릿은 notes로 되어있지만 모델은 notes로 저장
        
        # 전화번호 포맷팅
        if phone and phone.isdigit():
            # 숫자만 포함된 경우 하이픈 추가
            if len(phone) == 10:  # 예: 7142344901
                phone = f"{phone[:3]}-{phone[3:6]}-{phone[6:]}"
            elif len(phone) == 11:  # 예: 17142344901
                phone = f"{phone[:1]}-{phone[1:4]}-{phone[4:7]}-{phone[7:]}"
        
        # 입사일 처리
        try:
            # 설정에서 날짜 형식 가져오기
            config = load_config()
            date_format = config.get('date_format', 'YYYY-MM-DD')
            
            # 날짜 형식에 따라 처리
            if date_format == 'MM/DD/YYYY' and '/' in hire_date_str:
                # MM/DD/YYYY 형식을 YYYY-MM-DD로 변환
                month, day, year = hire_date_str.split('/')
                hire_date = datetime(int(year), int(month), int(day)).date()
            elif date_format == 'DD/MM/YYYY' and '/' in hire_date_str:
                # DD/MM/YYYY 형식을 YYYY-MM-DD로 변환
                day, month, year = hire_date_str.split('/')
                hire_date = datetime(int(year), int(month), int(day)).date()
            else:
                # 기본 YYYY-MM-DD 형식 처리
            hire_date = datetime.strptime(hire_date_str, '%Y-%m-%d').date() if hire_date_str else employee.hire_date
        except ValueError as e:
            flash(f'유효하지 않은 날짜 형식입니다: {str(e)}', 'danger')
            return redirect(url_for('edit_employee', id=id))
        
        # 직원 정보 업데이트
        employee.name = name
        employee.department = department
        employee.position = position
        employee.phone = phone
        employee.email = email
        employee.hire_date = hire_date
        employee.status = status  # 상태 필드 추가
        employee.address = address  # 주소 필드 추가
        employee.notes = notes  # notes로 수정
        
        try:
            db.session.commit()
            flash('직원 정보가 성공적으로 업데이트되었습니다.', 'success')
            return redirect(url_for('employees'))
        except Exception as e:
            db.session.rollback()
            flash(f'직원 정보 업데이트 중 오류가 발생했습니다: {str(e)}', 'danger')
            return redirect(url_for('edit_employee', id=id))
    
    # 설정에서 날짜 형식 가져오기
    config = load_config()
    date_format = config.get('date_format', 'YYYY-MM-DD')
    
    # 클라이언트에서 사용할 날짜 형식 변환
    js_date_format = 'yyyy-mm-dd'  # 기본값
    if date_format == 'MM/DD/YYYY':
        js_date_format = 'mm/dd/yyyy'
    elif date_format == 'DD/MM/YYYY':
        js_date_format = 'dd/mm/yyyy'
    
    return render_template('edit_employee.html', employee=employee, js_date_format=js_date_format)

@app.route('/delete_employee/<int:id>', methods=['POST'])
def delete_employee(id):
    employee = Employee.query.get_or_404(id)
    
    try:
        db.session.delete(employee)
        db.session.commit()
        flash('직원이 성공적으로 삭제되었습니다.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'직원 삭제 중 오류가 발생했습니다: {str(e)}', 'danger')
    
    return redirect(url_for('employees'))

@app.route('/view_employee/<int:id>')
def view_employee(id):
    employee = Employee.query.get_or_404(id)
    return render_template('view_employee.html', employee=employee)

@app.route('/orders')
def orders():
    # 검색 및 필터링 매개변수 처리
    search_query = request.args.get('search', '')
    status = request.args.get('status', '')
    date_range = request.args.get('date_range', '')
    
    # 페이지네이션 매개변수
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    # 기본 쿼리 생성
    query = db.session.query(Order).join(Customer).join(Employee)
    
    # 통합 검색 필터 적용
    if search_query:
        search_filter = db.or_(
            Order.order_id.like(f'%{search_query}%'),
            Customer.company_name.like(f'%{search_query}%'),
            Employee.name.like(f'%{search_query}%'),
            Order.status.like(f'%{search_query}%')
        )
        query = query.filter(search_filter)
    
    # 상태 필터 적용
    if status:
        query = query.filter(Order.status == status)
    
    # 날짜 범위 필터 적용
    if date_range:
            today = datetime.now().date()
        
        if date_range == '오늘':
            # 오늘 날짜의 주문만 필터링
            query = query.filter(db.func.date(Order.order_date) == today)
        elif date_range == '최근 일주일':
            # 최근 7일간의 주문 필터링
            week_ago = today - timedelta(days=7)
            query = query.filter(Order.order_date >= week_ago)
        elif date_range == '최근 한달':
            # 최근 30일간의 주문 필터링
            month_ago = today - timedelta(days=30)
            query = query.filter(Order.order_date >= month_ago)
        elif ' ~ ' in date_range:
            # 커스텀 날짜 범위 처리 (예: '2023-01-01 ~ 2023-01-31')
            start_date_str, end_date_str = date_range.split(' ~ ')
            try:
                start_date = datetime.strptime(start_date_str.strip(), '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date_str.strip(), '%Y-%m-%d').date()
                query = query.filter(Order.order_date >= start_date, Order.order_date <= end_date)
            except ValueError:
                # 날짜 형식이 잘못된 경우 필터링하지 않음
                pass
    
    # 주문 날짜 내림차순 정렬
    query = query.order_by(Order.order_date.desc())
    
    # 페이지네이션 적용
    orders_pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    orders = orders_pagination.items
    
    return render_template('orders.html', orders=orders, pagination=orders_pagination, search_query=search_query)

@app.route('/add_order', methods=['GET', 'POST'])
def add_order():
    if request.method == 'POST':
        try:
            # 주문 번호 처리
            manual_order_id = request.form.get('manual_order_id')
            if manual_order_id and manual_order_id.strip():
                # 수동 주문 번호 사용
                order_id = manual_order_id.strip()
                # 중복 확인
                existing_order = Order.query.filter_by(order_id=order_id).first()
                if existing_order:
                    flash(f'이미 존재하는 주문 번호입니다: {order_id}', 'danger')
                    customers = Customer.query.all()
                    products = Product.query.all()
                    employees = Employee.query.all()
                    return render_template('add_order.html', 
                                      customers=customers, 
                                      products=products, 
                                      employees=employees, 
                                      today=datetime.now().strftime('%m/%d/%Y'))
            else:
                # 자동 주문 번호 생성
                today = datetime.now().strftime('%Y%m%d')
                last_order = Order.query.filter(Order.order_id.like(f'ORD-{today}-%')).order_by(Order.order_id.desc()).first()
                
                if last_order:
                    try:
                        last_number = int(last_order.order_id.split('-')[-1])
                        new_number = last_number + 1
                    except (ValueError, IndexError):
                        new_number = 1
                else:
                    new_number = 1
                    
                order_id = f'ORD-{today}-{new_number:03d}'
            
            # 주문 기본 정보 가져오기
            customer_id = request.form.get('customer_id')
            
            # 날짜 변환 - 미국식 날짜(MM/DD/YYYY)를 ISO 형식(YYYY-MM-DD)으로 변환
            order_date_str = request.form.get('order_date')
            if '/' in order_date_str:  # MM/DD/YYYY 형식이면
                month, day, year = order_date_str.split('/')
                order_date = datetime(int(year), int(month), int(day))
            else:  # 이미 ISO 형식이면
                order_date = datetime.strptime(order_date_str, '%Y-%m-%d')
            
            delivery_date_str = request.form.get('delivery_date')
            delivery_date = None
            if delivery_date_str and delivery_date_str.strip():
                if '/' in delivery_date_str:  # MM/DD/YYYY 형식이면
                    month, day, year = delivery_date_str.split('/')
                    delivery_date = datetime(int(year), int(month), int(day))
                else:  # 이미 ISO 형식이면
                    delivery_date = datetime.strptime(delivery_date_str, '%Y-%m-%d')
            
            status = request.form.get('status', '준비중')
            if not status:
                status = '준비중'
            
            # employee_id 처리
            employee_id = None
            employee_id_str = request.form.get('employee_id')
            if employee_id_str and employee_id_str.strip():
                try:
                    employee_id = int(employee_id_str)
                except ValueError:
                    employee_id = None
            
            notes = request.form.get('notes', '')  # None이면 빈 문자열로 변환
            
            # 총 금액 계산
            total_amount = 0.0
            
            # 새 주문 생성
            new_order = Order(
                order_id=order_id,
                customer_id=customer_id,
                order_date=order_date,
                delivery_date=delivery_date,
                status=status,
                employee_id=employee_id,
                note=notes,
                total_amount=float(total_amount)
            )
            
            db.session.add(new_order)
            db.session.flush()  # 실제로 커밋하기 전에 데이터베이스에 플러시
            
            # 주문 항목 처리
            product_ids = request.form.getlist('product_id[]')
            quantities = request.form.getlist('quantity[]')
            unit_prices = request.form.getlist('unit_price[]')
            
            for i in range(len(product_ids)):
                if product_ids[i] and quantities[i] and unit_prices[i]:
                    product_id = product_ids[i]
                    try:
                        quantity = int(quantities[i])
                        unit_price = float(unit_prices[i].replace(',', ''))  # 천 단위 구분 기호 제거
                        subtotal = float(quantity * unit_price)
                        
                        # 주문 항목 추가
                        order_item = OrderItem(
                            order_id=new_order.order_id,
                            product_id=product_id,
                            quantity=quantity,
                            unit_price=unit_price,
                            subtotal=subtotal
                        )
                        
                        db.session.add(order_item)
                        total_amount += subtotal
                    except (ValueError, TypeError) as e:
                        print(f"주문 항목 처리 중 오류: {e}")
                        continue
            
            # 총 금액 업데이트
            new_order.total_amount = total_amount
            db.session.commit()
            
            flash('주문이 성공적으로 등록되었습니다.', 'success')
            return redirect(url_for('orders'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'주문 등록 중 오류가 발생했습니다: {str(e)}', 'danger')
            print(f"주문 등록 오류: {e}")
            import traceback
            print(traceback.format_exc())
            
            # GET 요청과 동일하게 처리하여 폼을 다시 표시
            customers = Customer.query.all()
            products = Product.query.all()
            employees = Employee.query.all()
            
            return render_template('add_order.html', 
                              customers=customers, 
                              products=products, 
                              employees=employees, 
                              today=datetime.now().strftime('%m/%d/%Y'))
    
    # GET 요청 처리
    customers = Customer.query.all()
    products = Product.query.all()
    employees = Employee.query.all()
    
    return render_template('add_order.html', 
                      customers=customers, 
                      products=products, 
                      employees=employees, 
                      today=datetime.now().strftime('%m/%d/%Y'))

@app.route('/edit_order/<order_id>', methods=['GET', 'POST'])
def edit_order(order_id):
    order = Order.query.filter_by(order_id=order_id).first_or_404()
    
    if request.method == 'POST':
        try:
            # 주문 기본 정보 업데이트
            order.customer_id = request.form.get('customer_id')
            
            # 날짜 변환 - 미국식 날짜(MM/DD/YYYY)를 ISO 형식(YYYY-MM-DD)으로 변환
            order_date_str = request.form.get('order_date')
            if '/' in order_date_str:  # MM/DD/YYYY 형식이면
                month, day, year = order_date_str.split('/')
                order.order_date = datetime(int(year), int(month), int(day))
            else:  # 이미 ISO 형식이면
                order.order_date = datetime.strptime(order_date_str, '%Y-%m-%d')
            
            delivery_date_str = request.form.get('delivery_date')
            order.delivery_date = None
            if delivery_date_str and delivery_date_str.strip():
                if '/' in delivery_date_str:  # MM/DD/YYYY 형식이면
                    month, day, year = delivery_date_str.split('/')
                    order.delivery_date = datetime(int(year), int(month), int(day))
                else:  # 이미 ISO 형식이면
                    order.delivery_date = datetime.strptime(delivery_date_str, '%Y-%m-%d')
            
            order.status = request.form.get('status')
            
            # employee_id 처리
            employee_id = None
            employee_id_str = request.form.get('employee_id')
            if employee_id_str and employee_id_str.strip():
                try:
                    employee_id = int(employee_id_str)
                except ValueError:
                    employee_id = None
            
            order.employee_id = employee_id
            order.note = request.form.get('notes', '')  # None이면 빈 문자열로 변환
            
            # 기존 주문 항목 삭제
            for item in order.order_items:
                db.session.delete(item)
            
            # 새 주문 항목 추가 및 총액 계산
            total_amount = 0.0
            product_ids = request.form.getlist('product_id[]')
            quantities = request.form.getlist('quantity[]')
            unit_prices = request.form.getlist('unit_price[]')
            
            for i in range(len(product_ids)):
                if product_ids[i] and quantities[i] and unit_prices[i]:
                    product_id = product_ids[i]
                    try:
                        quantity = int(quantities[i])
                        unit_price = float(unit_prices[i].replace(',', ''))  # 천 단위 구분 기호 제거
                        subtotal = float(quantity * unit_price)
                        
                        # 주문 항목 추가
                        order_item = OrderItem(
                            order_id=order.order_id,
                            product_id=product_id,
                            quantity=quantity,
                            unit_price=unit_price,
                            subtotal=subtotal
                        )
                        
                        db.session.add(order_item)
                        total_amount += subtotal
                    except (ValueError, TypeError) as e:
                        print(f"주문 항목 처리 중 오류: {e}")
                        continue
            
            # 총 금액 업데이트
            order.total_amount = total_amount
            order.updated_at = datetime.now()
            db.session.commit()
            
            flash('주문이 성공적으로 수정되었습니다.', 'success')
            return redirect(url_for('orders'))
        
        except Exception as e:
            db.session.rollback()
            flash(f'주문 수정 중 오류가 발생했습니다: {str(e)}', 'danger')
            print(f"주문 수정 오류: {e}")
            import traceback
            print(traceback.format_exc())
            
            # 다시 편집 폼으로 돌아가기
            customers = Customer.query.all()
            products = Product.query.all()
            employees = Employee.query.all()
            
            return render_template('edit_order.html', 
                              order=order,
                              customers=customers, 
                              products=products, 
                              employees=employees)
    
    # GET 요청 처리
    customers = Customer.query.all()
    products = Product.query.all()
    employees = Employee.query.all()
    
    return render_template('edit_order.html', 
                      order=order,
                      customers=customers, 
                      products=products, 
                      employees=employees)

@app.route('/delete_order/<order_id>', methods=['POST'])
def delete_order(order_id):
    try:
        # 주문 조회
    order = Order.query.filter_by(order_id=order_id).first_or_404()
    
        # 주문 삭제 (cascade 설정으로 인해 order_items도 자동 삭제됨)
        db.session.delete(order)
        db.session.commit()
        
        flash('주문이 성공적으로 삭제되었습니다.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'주문 삭제 중 오류가 발생했습니다: {str(e)}', 'danger')
    
    return redirect(url_for('orders'))

@app.route('/view_order/<order_id>')
def view_order(order_id):
    order = Order.query.filter_by(order_id=order_id).first_or_404()
    return render_template('view_order.html', order=order)

# 고객사의 담당자 정보 가져오기 API
@app.route('/api/get_customer_employee/<customer_id>', methods=['GET'])
def get_customer_employee(customer_id):
    try:
        customer = Customer.query.filter_by(customer_id=customer_id).first()
        if not customer:
            return jsonify({'success': False, 'message': '고객을 찾을 수 없습니다.'}), 404
            
        response_data = {
            'success': True,
            'employee_id': customer.employee_id,
            'note': customer.note or ''  # 고객의 메모 정보 추가 (null인 경우 빈 문자열 반환)
        }
        
        # 담당 직원 이름 추가하기
        if customer.employee_id:
            employee = Employee.query.get(customer.employee_id)
            if employee:
                response_data['employee_name'] = employee.name
        
        return jsonify(response_data)
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'오류가 발생했습니다: {str(e)}'
        }), 500

# 테스트 페이지 라우트 추가
@app.route('/test')
def test_page():
    return render_template('test.html')

# Pick Ticket 생성 및 표시
@app.route('/pick_ticket/<order_id>')
def pick_ticket(order_id):
    # SQLAlchemy ORM을 사용하여 주문 정보 가져오기
    order = Order.query.filter_by(order_id=order_id).first_or_404()
    
    # 주문 항목과 제품 정보를 함께 가져오기
    order_items_query = db.session.query(OrderItem, Product).join(
        Product, OrderItem.product_id == Product.product_id
    ).filter(
        OrderItem.order_id == order_id
    ).order_by(
        Product.sort_order, Product.product_name
    ).all()
    
    # 주문 항목 처리
    order_items = []
    for order_item, product in order_items_query:
        item_data = {
            'order_item_id': order_item.id,
            'quantity': order_item.quantity,
            'unit_price': float(order_item.unit_price),
            'product_id': product.product_id,
            'product_name': product.product_name,
            'location': product.location,
            'storage_location': product.storage_location,
            'box_quantity': product.box_quantity,
            'individual_weight': product.individual_weight,
            'weight_unit': product.weight_unit,
            'sort_order': product.sort_order,
            'subtotal': float(order_item.quantity * order_item.unit_price)
        }
        order_items.append(item_data)
    
    # 총 금액 계산
    total_amount = sum(item['subtotal'] for item in order_items)
    
    # 현재 날짜 및 시간
    current_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    return render_template('pick_ticket.html', 
                          order=order, 
                          order_items=order_items, 
                          total_amount=total_amount,
                          print_datetime=current_datetime)

@app.route('/api/test/connection')
def test_connection():
    try:
        # 데이터베이스 연결 테스트
        db.session.execute('SELECT 1')
        return jsonify({
            'success': True,
            'message': '데이터베이스 연결이 정상입니다.',
            'details': {
                'database_type': 'SQLite',
                'status': 'connected'
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'데이터베이스 연결 오류: {str(e)}',
            'details': None
        })

@app.route('/api/test/config')
def test_config():
    try:
        config = load_config()
        return jsonify({
            'success': True,
            'message': '설정 파일이 정상적으로 로드되었습니다.',
            'details': config
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'설정 파일 로드 오류: {str(e)}',
            'details': None
        })

@app.route('/api/test/search')
def test_search():
    try:
        # 검색 기능 테스트
        products = Product.query.limit(5).all()
        customers = Customer.query.limit(5).all()
        orders = Order.query.limit(5).all()
        
        return jsonify({
            'success': True,
            'message': '검색 기능이 정상적으로 작동합니다.',
            'details': {
                'products_count': len(products),
                'customers_count': len(customers),
                'orders_count': len(orders)
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'검색 기능 테스트 오류: {str(e)}',
            'details': None
        })

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # 데이터베이스 초기화 및 샘플 데이터 추가
        add_sample_data()
    app.run(host='0.0.0.0', port=8080, debug=True) 