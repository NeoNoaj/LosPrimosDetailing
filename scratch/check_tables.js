const mysql = require('mysql2/promise');

const dbConfig = {
    host: 'localhost',
    user: 'root',
    password: 'BerserkCR21.',
    database: 'losprimosdetailing_db'
};

async function checkTables() {
    try {
        const connection = await mysql.createConnection(dbConfig);
        const [rows] = await connection.query('SHOW TABLES');
        console.log(JSON.stringify(rows));
        await connection.end();
    } catch (err) {
        console.error(err.message);
    }
}

checkTables();
