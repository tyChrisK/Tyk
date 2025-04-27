-- 제품 정보 테이블 생성
CREATE TABLE products (
    product_id VARCHAR(20) PRIMARY KEY,
    product_name VARCHAR(100) NOT NULL,
    product_name_en VARCHAR(100),
    category VARCHAR(50) NOT NULL,
    purchase_price DECIMAL(10,2) NOT NULL,
    selling_price DECIMAL(10,2) NOT NULL,
    standard_quantity INT NOT NULL,
    current_stock INT NOT NULL DEFAULT 0,
    minimum_stock INT NOT NULL,
    weight_unit ENUM('oz', 'kg', 'g', 'lb') NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- 입출고 기록 테이블 생성
CREATE TABLE inventory_transactions (
    transaction_id INT AUTO_INCREMENT PRIMARY KEY,
    product_id VARCHAR(20) NOT NULL,
    individual_barcode VARCHAR(50),
    box_barcode VARCHAR(50),
    pallet_barcode VARCHAR(50),
    transaction_type ENUM('입고', '출고') NOT NULL,
    quantity INT NOT NULL,
    expiration_date DATE,
    transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);

-- 바코드 인덱스 생성
CREATE INDEX idx_individual_barcode ON inventory_transactions(individual_barcode);
CREATE INDEX idx_box_barcode ON inventory_transactions(box_barcode);
CREATE INDEX idx_pallet_barcode ON inventory_transactions(pallet_barcode);

-- 트랜잭션 날짜 인덱스 생성
CREATE INDEX idx_transaction_date ON inventory_transactions(transaction_date);

-- 제품명 검색을 위한 인덱스
CREATE INDEX idx_product_name ON products(product_name);
CREATE INDEX idx_product_name_en ON products(product_name_en);

-- 제품 정보 기본 확인
SELECT 
    COUNT(*) as total_products,
    COUNT(DISTINCT product_id) as unique_products,
    COUNT(DISTINCT category) as unique_categories
FROM products;

-- 재고 수량 검증
SELECT 
    p.product_id,
    p.product_name,
    p.current_stock,
    (
        SELECT SUM(CASE WHEN transaction_type = '입고' THEN quantity ELSE -quantity END)
        FROM inventory_transactions
        WHERE product_id = p.product_id
    ) as calculated_stock
FROM products p
HAVING current_stock != calculated_stock;

-- 유통기한 임박 제품 확인
SELECT 
    p.product_name,
    t.expiration_date,
    DATEDIFF(t.expiration_date, CURDATE()) as days_remaining
FROM inventory_transactions t
JOIN products p ON t.product_id = p.product_id
WHERE t.expiration_date IS NOT NULL
    AND t.transaction_type = '입고'
    AND DATEDIFF(t.expiration_date, CURDATE()) <= 7
ORDER BY days_remaining;

-- 최소 재고량 이하 제품 확인
SELECT 
    product_id,
    product_name,
    current_stock,
    minimum_stock
FROM products
WHERE current_stock <= minimum_stock; 