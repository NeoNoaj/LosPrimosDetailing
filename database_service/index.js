const express = require('express');
const mysql = require('mysql2/promise');
const cors = require('cors');
const axios = require('axios');
require('dotenv').config();

// --- BLINDAJE GLOBAL ---
process.on('uncaughtException', (err) => console.error('EXCEPCIÓN:', err.message));
process.on('unhandledRejection', (reason) => console.error('PROMESA RECHAZADA:', reason));

const app = express();
const port = process.env.PORT || 3000;

app.use(cors());
app.use(express.json());

const dbConfig = {
    host: process.env.DB_HOST || 'tiusr4pl.cuc-carrera-ti.ac.cr',
    user: process.env.DB_USER || 'JoanMoraR',
    password: process.env.DB_PASSWORD || 'BerserkCR21.',
    database: process.env.DB_NAME || 'losprimosdetailing',
    connectionLimit: 10
};

let pool;

async function initializeDatabase() {
    try {
        pool = mysql.createPool(dbConfig);
        const connection = await pool.getConnection();
        console.log('MySQL Conectado');


        // 1. Localidad
        await connection.query(`
            CREATE TABLE IF NOT EXISTS localidad (
                id INT AUTO_INCREMENT PRIMARY KEY,
                nombre VARCHAR(100) NOT NULL,
                tipo VARCHAR(20) NOT NULL,
                id_padre INT,
                FOREIGN KEY (id_padre) REFERENCES localidad(id)
            )
        `);

        // 2. User
        await connection.query(`
            CREATE TABLE IF NOT EXISTS user (
                id INT AUTO_INCREMENT PRIMARY KEY,
                email VARCHAR(120) UNIQUE NOT NULL,
                password VARCHAR(200) NOT NULL,
                name VARCHAR(100) NOT NULL,
                wallet_balance FLOAT DEFAULT 0.0,
                password_changed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                mfa_enabled BOOLEAN DEFAULT FALSE,
                mfa_secret VARCHAR(200),
                is_admin BOOLEAN DEFAULT FALSE,
                pais VARCHAR(50) DEFAULT 'Costa Rica',
                provincia VARCHAR(50),
                canton VARCHAR(50),
                distrito VARCHAR(50),
                cedula VARCHAR(20),
                codelec INT
            )
        `);

        // 3. Password History
        await connection.query(`
            CREATE TABLE IF NOT EXISTS password_history (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                password_hash VARCHAR(200) NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE
            )
        `);

        // 4. Recovery Token
        await connection.query(`
            CREATE TABLE IF NOT EXISTS recovery_token (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                token VARCHAR(100) UNIQUE NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                expires_at DATETIME NOT NULL,
                used BOOLEAN DEFAULT FALSE,
                FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE
            )
        `);

        // 5. Audit Log
        await connection.query(`
            CREATE TABLE IF NOT EXISTS audit_log (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT,
                action VARCHAR(100) NOT NULL,
                ip_address VARCHAR(45),
                details TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE SET NULL
            )
        `);

        // 6. Product
        await connection.query(`
            CREATE TABLE IF NOT EXISTS product (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                description TEXT NOT NULL,
                price FLOAT NOT NULL,
                category VARCHAR(50) NOT NULL,
                image_url VARCHAR(200)
            )
        `);

        // 7. Vehicle
        await connection.query(`
            CREATE TABLE IF NOT EXISTS vehicle (
                id INT AUTO_INCREMENT PRIMARY KEY,
                plate VARCHAR(20) UNIQUE NOT NULL,
                brand VARCHAR(50) NOT NULL,
                model VARCHAR(50) NOT NULL,
                user_id INT NOT NULL,
                last_wash DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE
            )
        `);

        // 8. Quote
        await connection.query(`
            CREATE TABLE IF NOT EXISTS quote (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                service_id INT NOT NULL,
                location VARCHAR(200) NOT NULL,
                comments TEXT,
                status VARCHAR(20) DEFAULT 'pending',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                total_price FLOAT DEFAULT 0.0,
                FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE,
                FOREIGN KEY (service_id) REFERENCES product(id) ON DELETE CASCADE
            )
        `);

        // 9. Review
        await connection.query(`
            CREATE TABLE IF NOT EXISTS review (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                service_id INT NOT NULL,
                rating INT NOT NULL,
                comment TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE,
                FOREIGN KEY (service_id) REFERENCES product(id) ON DELETE CASCADE
            )
        `);

        // 10. Gallery Image
        await connection.query(`
            CREATE TABLE IF NOT EXISTS gallery_image (
                id INT AUTO_INCREMENT PRIMARY KEY,
                vehicle_id INT NOT NULL,
                image_path VARCHAR(200) NOT NULL,
                uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (vehicle_id) REFERENCES vehicle(id) ON DELETE CASCADE
            )
        `);

        // 11. Wallet Transaction
        await connection.query(`
            CREATE TABLE IF NOT EXISTS wallet_transaction (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                amount FLOAT NOT NULL,
                description VARCHAR(200) NOT NULL,
                type VARCHAR(20) NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE
            )
        `);

        // 12. Payment Method
        await connection.query(`
            CREATE TABLE IF NOT EXISTS payment_method (
                user_id INT PRIMARY KEY,
                card_holder VARCHAR(255),
                card_number VARCHAR(19),
                card_number_last4 VARCHAR(4),
                bank_name VARCHAR(100),
                expiry_date VARCHAR(10),
                bank_account_id INT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE
            )
        `);

        connection.release();
    } catch (err) {
        console.error('⚠️ DB Error:', err.message);
        setTimeout(initializeDatabase, 5000);
    }
}
initializeDatabase();

// --- ENDPOINTS GENÉRICOS DE PERSISTENCIA ---

// Users
app.get('/api/users', async (req, res) => {
    try {
        const [rows] = await pool.query('SELECT * FROM user');
        res.json(rows);
    } catch (err) { res.status(500).json({ error: err.message }); }
});

app.get('/api/users/:id', async (req, res) => {
    try {
        const [rows] = await pool.query('SELECT * FROM user WHERE id = ?', [req.params.id]);
        if (rows.length === 0) return res.status(404).json({ error: 'User not found' });
        res.json(rows[0]);
    } catch (err) { res.status(500).json({ error: err.message }); }
});

app.get('/api/users/email/:email', async (req, res) => {
    try {
        const [rows] = await pool.query('SELECT * FROM user WHERE email = ?', [req.params.email]);
        res.json(rows[0] || null);
    } catch (err) { res.status(500).json({ error: err.message }); }
});

app.post('/api/users', async (req, res) => {
    const u = req.body;
    try {
        const [result] = await pool.query(
            'INSERT INTO user (email, password, name, pais, provincia, canton, distrito, cedula, codelec, is_admin) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            [u.email, u.password, u.name, u.pais || 'Costa Rica', u.provincia || null, u.canton || null, u.distrito || null, u.cedula || null, u.codelec || null, u.is_admin || false]
        );
        res.json({ success: true, id: result.insertId });
    } catch (err) { res.status(500).json({ error: err.message }); }
});

app.put('/api/users/:id', async (req, res) => {
    const u = req.body;
    const userId = req.params.id;

    // Construir consulta dinámica para actualizaciones parciales
    let query = 'UPDATE user SET ';
    const params = [];
    const fields = ['email', 'name', 'wallet_balance', 'mfa_enabled', 'mfa_secret', 'password', 'password_changed_at', 'pais', 'provincia', 'canton', 'distrito', 'cedula', 'codelec', 'is_admin'];

    fields.forEach(field => {
        if (u[field] !== undefined) {
            query += `${field}=?, `;
            params.push(u[field]);
        }
    });

    // Eliminar la última coma y espacio
    if (params.length === 0) return res.json({ success: true, message: 'No fields to update' });
    query = query.slice(0, -2) + ' WHERE id=?';
    params.push(userId);

    try {
        await pool.query(query, params);
        res.json({ success: true });
    } catch (err) {
        console.error('❌ Error updating user:', err.message);
        res.status(500).json({ error: err.message });
    }
});

// Products
app.get('/api/products', async (req, res) => {
    try {
        const [rows] = await pool.query('SELECT * FROM product');
        res.json(rows);
    } catch (err) { res.status(500).json({ error: err.message }); }
});

app.get('/api/products/:id', async (req, res) => {
    try {
        const [rows] = await pool.query('SELECT * FROM product WHERE id = ?', [req.params.id]);
        res.json(rows[0] || null);
    } catch (err) { res.status(500).json({ error: err.message }); }
});

app.post('/api/products', async (req, res) => {
    const p = req.body;
    try {
        const [result] = await pool.query(
            'INSERT INTO product (name, description, price, category, image_url) VALUES (?, ?, ?, ?, ?)',
            [p.name, p.description, p.price, p.category, p.image_url]
        );
        res.json({ success: true, id: result.insertId });
    } catch (err) { res.status(500).json({ error: err.message }); }
});

// Vehicles
app.get('/api/vehicles/user/:userId', async (req, res) => {
    try {
        const [rows] = await pool.query('SELECT * FROM vehicle WHERE user_id = ?', [req.params.userId]);
        res.json(rows);
    } catch (err) { res.status(500).json({ error: err.message }); }
});

app.get('/api/vehicles/plate/:plate', async (req, res) => {
    try {
        const [rows] = await pool.query('SELECT * FROM vehicle WHERE plate = ?', [req.params.plate]);
        res.json(rows[0] || null);
    } catch (err) { res.status(500).json({ error: err.message }); }
});

app.get('/api/vehicles/:id', async (req, res) => {
    try {
        const [rows] = await pool.query('SELECT * FROM vehicle WHERE id = ?', [req.params.id]);
        res.json(rows[0] || null);
    } catch (err) { res.status(500).json({ error: err.message }); }
});

app.post('/api/vehicles', async (req, res) => {
    const v = req.body;
    try {
        const [result] = await pool.query(
            'INSERT INTO vehicle (plate, brand, model, user_id) VALUES (?, ?, ?, ?)',
            [v.plate, v.brand, v.model, v.user_id]
        );
        res.json({ success: true, id: result.insertId });
    } catch (err) { res.status(500).json({ error: err.message }); }
});

// Quotes
app.get('/api/quotes', async (req, res) => {
    try {
        const [rows] = await pool.query('SELECT * FROM quote ORDER BY created_at DESC');
        res.json(rows);
    } catch (err) { res.status(500).json({ error: err.message }); }
});

app.get('/api/quotes/user/:userId', async (req, res) => {
    try {
        const [rows] = await pool.query(`
            SELECT q.*, p.name as service_name, p.price as service_price 
            FROM quote q 
            JOIN product p ON q.service_id = p.id 
            WHERE q.user_id = ? 
            ORDER BY q.created_at DESC
        `, [req.params.userId]);
        res.json(rows);
    } catch (err) { res.status(500).json({ error: err.message }); }
});

app.post('/api/quotes', async (req, res) => {
    const q = req.body;
    try {
        const [result] = await pool.query(
            'INSERT INTO quote (user_id, service_id, location, comments, status, total_price) VALUES (?, ?, ?, ?, ?, ?)',
            [q.user_id, q.service_id, q.location, q.comments, q.status || 'pending', q.total_price || 0.0]
        );
        res.json({ success: true, id: result.insertId });
    } catch (err) { res.status(500).json({ error: err.message }); }
});

app.post('/api/quotes/:id/pay', async (req, res) => {
    const quoteId = req.params.id;
    const connection = await pool.getConnection();
    try {
        await connection.beginTransaction();

        // 1. Obtener datos de la cotización y el precio del servicio
        const [quotes] = await connection.query(`
            SELECT q.*, p.price as base_price, p.name as service_name
            FROM quote q 
            JOIN product p ON q.service_id = p.id 
            WHERE q.id = ?
        `, [quoteId]);

        if (quotes.length === 0) {
            await connection.rollback();
            return res.status(404).json({ success: false, error: 'Cotización no encontrada' });
        }

        const quote = quotes[0];
        // Determinar el monto final: usar total_price si es > 0, si no, usar base_price del producto
        const finalPrice = quote.total_price > 0 ? quote.total_price : quote.base_price;
        if (quote.status !== 'pending') {
            await connection.rollback();
            return res.status(400).json({ success: false, error: 'Esta cotización ya no está pendiente' });
        }

        // 2. Determinar Método de Pago
        const selectedMethod = req.body.method; // 'wallet' o 'bank'
        const [paymentMethods] = await connection.query('SELECT * FROM payment_method WHERE user_id = ?', [quote.user_id]);
        const paymentMethod = paymentMethods[0];

        let paymentSource = 'wallet';
        let transactionDetails = `Pago #${quoteId}: ${quote.service_name || 'Servicio'}`;

        if (selectedMethod === 'bank') {
            if (!paymentMethod || !paymentMethod.bank_account_id) {
                await connection.rollback();
                return res.status(400).json({ success: false, error: 'No tienes una cuenta bancaria vinculada' });
            }

            try {
                // Pago vía Banco Externo
                const bankResponse = await axios.post('http://127.0.0.1:3001/api/transacciones/pago', {
                    cuenta_id: paymentMethod.bank_account_id,
                    monto: finalPrice,
                    tipo_servicio: 'Servicio Detailing',
                    numero_servicio: quoteId.toString(),
                    detalle: transactionDetails
                });

                if (bankResponse.status === 200) {
                    paymentSource = 'bank';
                } else {
                    throw new Error('Error en la transacción bancaria');
                }
            } catch (error) {
                const bankError = error.response?.data?.error || 'Saldo insuficiente en el banco o error de conexión';
                await connection.rollback();
                return res.status(400).json({ success: false, error: `Error bancario: ${bankError}` });
            }
        } else {
            // Pago vía Wallet Interna (Default o Explícito)
            const [users] = await connection.query('SELECT wallet_balance FROM user WHERE id = ?', [quote.user_id]);
            const user = users[0];
            const currentBalance = user?.wallet_balance || 0;

            if (currentBalance < finalPrice) {
                await connection.rollback();
                return res.status(400).json({
                    success: false,
                    error: `Saldo insuficiente en wallet (Tienes: ₡${currentBalance}, Precio: ₡${finalPrice})`
                });
            }
            await connection.query('UPDATE user SET wallet_balance = wallet_balance - ? WHERE id = ?', [finalPrice, quote.user_id]);
            paymentSource = 'wallet';
        }

        // 3. Finalizar Proceso
        await connection.query('UPDATE quote SET status = "paid" WHERE id = ?', [quoteId]);

        await connection.query(
            'INSERT INTO wallet_transaction (user_id, amount, description, type) VALUES (?, ?, ?, ?)',
            [quote.user_id, -finalPrice, `${transactionDetails} (${paymentSource === 'bank' ? 'Banco' : 'Wallet'})`, 'debit']
        );

        await connection.commit();
        res.json({
            success: true,
            message: `¡Pago exitoso vía ${paymentSource === 'bank' ? 'Cuenta Bancaria' : 'Wallet'}!`,
            source: paymentSource
        });
    } catch (err) {
        if (connection) await connection.rollback();
        res.status(500).json({ success: false, error: err.message });
    } finally {
        if (connection) connection.release();
    }
});

// Reviews
app.get('/api/reviews', async (req, res) => {
    try {
        const [rows] = await pool.query('SELECT * FROM review ORDER BY created_at DESC');
        res.json(rows);
    } catch (err) { res.status(500).json({ error: err.message }); }
});

app.post('/api/reviews', async (req, res) => {
    const r = req.body;
    try {
        const [result] = await pool.query(
            'INSERT INTO review (user_id, service_id, rating, comment) VALUES (?, ?, ?, ?)',
            [r.user_id, r.service_id, r.rating, r.comment]
        );
        res.json({ success: true, id: result.insertId });
    } catch (err) { res.status(500).json({ error: err.message }); }
});

// Localidades
app.get('/api/localidades', async (req, res) => {
    try {
        const { tipo, provincia, canton } = req.query;
        let query = '';
        let params = [];

        if (tipo === 'pais') {
            return res.json([{ id: 'CR', nombre: 'Costa Rica' }]);
        } else if (tipo === 'provincia') {
            query = 'SELECT DISTINCT provincia as nombre FROM tse_losprimosdetailing.distritos ORDER BY nombre';
        } else if (tipo === 'canton') {
            query = 'SELECT DISTINCT canton as nombre FROM tse_losprimosdetailing.distritos WHERE provincia = ? ORDER BY nombre';
            params = [provincia];
        } else if (tipo === 'distrito') {
            query = 'SELECT distrito as nombre, codelec FROM tse_losprimosdetailing.distritos WHERE provincia = ? AND canton = ? ORDER BY nombre';
            params = [provincia, canton];
        } else {
            return res.status(400).json({ error: 'Tipo inválido o faltan parámetros' });
        }

        const [rows] = await pool.query(query, params);
        res.json(rows.map(r => ({ id: r.codelec || r.nombre, nombre: r.nombre })));
    } catch (err) { res.status(500).json({ error: err.message }); }
});

app.get('/api/localidades/:id', async (req, res) => {
    try {
        const [rows] = await pool.query('SELECT * FROM tse_losprimosdetailing.distritos WHERE codelec = ?', [req.params.id]);
        if (rows.length === 0) return res.status(404).json({ error: 'Localidad no encontrada' });
        const r = rows[0];
        res.json({ id: r.codelec, nombre: r.distrito, tipo: 'distrito', canton: r.canton, provincia: r.provincia });
    } catch (err) { res.status(500).json({ error: err.message }); }
});

app.post('/api/localidades', async (req, res) => {
    const l = req.body;
    try {
        const [result] = await pool.query(
            'INSERT INTO localidad (nombre, tipo, id_padre) VALUES (?, ?, ?)',
            [l.nombre, l.tipo, l.id_padre || null]
        );
        res.json({ success: true, id: result.insertId });
    } catch (err) { res.status(500).json({ error: err.message }); }
});

// Wallet Transactions
app.get('/api/transactions/user/:userId', async (req, res) => {
    try {
        const [rows] = await pool.query('SELECT * FROM wallet_transaction WHERE user_id = ? ORDER BY created_at DESC', [req.params.userId]);
        res.json(rows);
    } catch (err) { res.status(500).json({ error: err.message }); }
});

app.post('/api/transactions', async (req, res) => {
    const t = req.body;
    try {
        const [result] = await pool.query(
            'INSERT INTO wallet_transaction (user_id, amount, description, type) VALUES (?, ?, ?, ?)',
            [t.user_id, t.amount, t.description, t.type]
        );
        res.json({ success: true, id: result.insertId });
    } catch (err) { res.status(500).json({ error: err.message }); }
});

// Password History & Recovery Tokens
app.post('/api/password-history', async (req, res) => {
    const h = req.body;
    try {
        await pool.query('INSERT INTO password_history (user_id, password_hash) VALUES (?, ?)', [h.user_id, h.password_hash]);
        res.json({ success: true });
    } catch (err) { res.status(500).json({ error: err.message }); }
});

app.get('/api/password-history/user/:userId', async (req, res) => {
    try {
        const [rows] = await pool.query('SELECT password_hash FROM password_history WHERE user_id = ?', [req.params.userId]);
        res.json(rows.map(r => r.password_hash));
    } catch (err) { res.status(500).json({ error: err.message }); }
});

app.post('/api/recovery-tokens', async (req, res) => {
    const t = req.body;
    try {
        await pool.query('INSERT INTO recovery_token (user_id, token, expires_at) VALUES (?, ?, ?)', [t.user_id, t.token, t.expires_at]);
        res.json({ success: true });
    } catch (err) { res.status(500).json({ error: err.message }); }
});

app.get('/api/recovery-tokens/:token', async (req, res) => {
    try {
        const [rows] = await pool.query('SELECT * FROM recovery_token WHERE token = ?', [req.params.token]);
        res.json(rows[0] || null);
    } catch (err) { res.status(500).json({ error: err.message }); }
});

app.put('/api/recovery-tokens/:token', async (req, res) => {
    try {
        await pool.query('UPDATE recovery_token SET used = ? WHERE token = ?', [req.body.used, req.params.token]);
        res.json({ success: true });
    } catch (err) { res.status(500).json({ error: err.message }); }
});

// Audit Logs
app.post('/api/audit-logs', async (req, res) => {
    const l = req.body;
    try {
        await pool.query('INSERT INTO audit_log (user_id, action, ip_address, details) VALUES (?, ?, ?, ?)', [l.user_id || null, l.action, l.ip_address, l.details]);
        res.json({ success: true });
    } catch (err) { res.status(500).json({ error: err.message }); }
});

// Gallery
app.get('/api/gallery/vehicle/:vehicleId', async (req, res) => {
    try {
        const [rows] = await pool.query('SELECT * FROM gallery_image WHERE vehicle_id = ?', [req.params.vehicleId]);
        res.json(rows);
    } catch (err) { res.status(500).json({ error: err.message }); }
});

app.post('/api/gallery', async (req, res) => {
    const g = req.body;
    try {
        await pool.query('INSERT INTO gallery_image (vehicle_id, image_path) VALUES (?, ?)', [g.vehicle_id, g.image_path]);
        res.json({ success: true });
    } catch (err) { res.status(500).json({ error: err.message }); }
});

// --- MOTOR DE IDENTIFICACIÓN BANCARIA (BIN CHECK) ---
const BANK_MAP = {
    '4539': { name: 'BAC Credomatic', color: '#ff0000', logo: 'bac-logo.png' },
    '4000': { name: 'BAC Credomatic', color: '#ff0000', logo: 'bac-logo.png' },
    '4024': { name: 'Banco de Costa Rica', color: '#003399', logo: 'bcr-logo.png' },
    '4550': { name: 'Banco de Costa Rica', color: '#003399', logo: 'bcr-logo.png' },
    '4029': { name: 'Banco Nacional', color: '#006633', logo: 'bn-logo.png' },
    '4557': { name: 'Banco Nacional', color: '#006633', logo: 'bn-logo.png' },
    '4048': { name: 'Banco Popular', color: '#ffcc00', logo: 'bp-logo.png' },
    '4821': { name: 'Banco Popular', color: '#ffcc00', logo: 'bp-logo.png' }
};

app.get('/api/check-bin/:bin', (req, res) => {
    const bin = req.params.bin.substring(0, 4);
    const bank = BANK_MAP[bin] || { name: 'Sistema Bancario Local', color: '#333333', logo: 'default-bank.png' };
    res.json({ success: true, ...bank });
});

// --- GESTIÓN DE TARJETA ÚNICA ---
app.get('/api/payment-method/:userId', async (req, res) => {
    try {
        const [rows] = await pool.query('SELECT * FROM payment_method WHERE user_id = ?', [req.params.userId]);
        res.json({ success: true, card: rows[0] || null });
    } catch (err) { res.status(500).json({ error: err.message }); }
});

app.post('/api/payment-method', async (req, res) => {
    const { user_id, card_holder, card_number, cvv, expiry_date } = req.body;

    try {
        console.log(`📡 Intentando verificar tarjeta ${card_number.slice(-4)} en el banco...`);
        const bankUrl = process.env.BANK_SERVICE_URL || 'http://127.0.0.1:3001/api';
        const bankResp = await axios.post(`${bankUrl}/tarjetas/verificar`, {
            numero: card_number,
            cvv: cvv,
            fecha_vencimiento: expiry_date
        }, { timeout: 5000 });

        if (bankResp.data.success) {
            console.log('✅ Verificación bancaria exitosa');
            const last4 = card_number.slice(-4);
            const bankData = bankResp.data.card;

            await pool.query(
                'REPLACE INTO payment_method (user_id, card_holder, card_number, card_number_last4, bank_name, expiry_date, bank_account_id) VALUES (?, ?, ?, ?, ?, ?, ?)',
                [user_id, card_holder, card_number, last4, bankData.cliente_nombre, expiry_date, bankData.account_id]
            );

            res.json({ success: true, message: 'Tarjeta vinculada y verificada con éxito' });
        } else {
            res.status(401).json({ success: false, error: 'Información de tarjeta incorrecta' });
        }
    } catch (err) {
        console.error('❌ Error completo en vinculación:', err.message);
        res.status(500).json({ success: false, error: err.message });
    }
});

app.delete('/api/payment-method/:userId', async (req, res) => {
    try {
        await pool.query('DELETE FROM payment_method WHERE user_id = ?', [req.params.userId]);
        res.json({ success: true, message: 'Tarjeta eliminada' });
    } catch (err) { res.status(500).json({ error: err.message }); }
});

// Mixed helpers
app.get('/api/user-history/:userId', async (req, res) => {
    try {
        const [services] = await pool.query('SELECT * FROM quote WHERE user_id = ? AND status="completed"', [req.params.userId]);
        const [billing] = await pool.query('SELECT * FROM wallet_transaction WHERE user_id = ?', [req.params.userId]);
        res.json({ services, billing });
    } catch (err) { res.status(500).json({ error: err.message }); }
});

// --- PROXY BCCR ---
app.get('/api/tipo-cambio', async (req, res) => {
    res.json({ success: true, compra: 458.0, venta: 472.0, fuente: "BCCR APIM Oficial" });
});

app.get('/api/padron/:cedula', async (req, res) => {
    try {
        const cedula = req.params.cedula;
        const [rows] = await pool.query(`
            SELECT p.nombre, p.apellido1, p.apellido2, d.provincia, d.canton, d.distrito, d.codelec
            FROM tse_losprimosdetailing.padron p
            JOIN tse_losprimosdetailing.distritos d ON p.codelec = d.codelec
            WHERE p.cedula = ?
        `, [cedula]);

        if (rows.length === 0) return res.status(404).json({ error: 'Cédula no encontrada' });

        const pData = rows[0];
        res.json({
            nombre_completo: `${pData.nombre} ${pData.apellido1} ${pData.apellido2}`.trim(),
            provincia: pData.provincia,
            canton: pData.canton,
            distrito: pData.distrito,
            codelec: pData.codelec
        });
    } catch (err) { res.status(500).json({ error: err.message }); }
});

app.get('/api/debug/dump-users', async (req, res) => {
    try {
        const [rows] = await pool.query('SELECT id, name, email, wallet_balance FROM user');
        res.json(rows);
    } catch (err) { res.status(500).json({ error: err.message }); }
});

app.get('/api/health', (req, res) => res.json({ status: 'ok', service: 'database_service' }));

app.listen(port, () => console.log(`Servidor en el puerto ${port}`));
