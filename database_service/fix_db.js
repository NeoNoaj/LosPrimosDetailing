const mysql = require('mysql2/promise');

const dbConfig = {
    host: 'tiusr4pl.cuc-carrera-ti.ac.cr',
    user: 'JoanMoraR',
    password: 'BerserkCR21.',
    database: 'losprimosdetailing'
};

async function fix() {
    const connection = await mysql.createConnection(dbConfig);
    console.log('Connected to DB');
    try {
        await connection.query('ALTER TABLE quote ADD COLUMN total_price FLOAT DEFAULT 0.0');
        console.log('Column added successfully');
    } catch (e) {
        console.log(e.message);
    }
    await connection.end();
}
fix();
