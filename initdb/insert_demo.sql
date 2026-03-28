INSERT INTO categories (name) VALUES
('Laptops'),
('Smartphones'),
('Accessories');

INSERT INTO customers (full_name, email, phone) VALUES
('Иван Иванов', 'ivan.ivanov@mail.ru', '+79775443223'),
('Мария Петрова', 'maria.petrova@mail.ru', '+79245864397');

INSERT INTO products (name, price, stock, category_id) VALUES
('MacBook Air M2', 1200.00, 10, 1),
('Lenovo ThinkPad X1', 1500.00, 5, 1),
('iPhone 15 Pro', 1300.00, 7, 2),
('Samsung Galaxy S24', 1100.00, 8, 2),
('USB-C Charger 65W', 35.50, 50, 3);

INSERT INTO orders (customer_id, status) VALUES
(1, 'NEW'),
(2, 'PAID');

INSERT INTO order_items (order_id, product_id, quantity, price) VALUES
(1, 1, 1, 1200.00),
(1, 5, 2, 35.50),
(2, 3, 1, 1300.00),
(2, 5, 1, 35.50);
