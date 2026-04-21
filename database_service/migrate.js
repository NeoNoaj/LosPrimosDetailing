const mysql = require('mysql2/promise');
require('dotenv').config();

const dbConfig = {
    host: 'localhost',
    user: 'root',
    password: 'BerserkCR21.',
    database: 'losprimosdetailing_db'
};

async function migrate() {
    try {
        const connection = await mysql.createConnection(dbConfig);
        console.log('✅ Connected to MySQL for migration');
        
        // Check if column exists
        const [rows] = await connection.query(`
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = 'losprimosdetailing_db' 
            AND TABLE_NAME = 'quote' 
            AND COLUMN_NAME = 'total_price'
        `);

        if (rows.length === 0) {
            console.log('⚠️ Column total_price missing. Adding it...');
            await connection.query(`
                ALTER TABLE quote ADD COLUMN total_price FLOAT DEFAULT 0.0
            `);
            console.log('✅ Column total_price added successfully');
        } else {
            console.log('✅ Column total_price already exists');
        }
        
        await connection.end();
    } catch (err) {
        console.error('❌ Migration Error:', err.message);
    }
}

migrate();
