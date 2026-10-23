//! Run only after the operator has selected an isolated or approved database.
#[tokio::main]
async fn main() {
    let result = async {
        let url = std::env::var("MIGRATION_DATABASE_URL").map_err(|_| ())?;
        let pool = sqlx::postgres::PgPoolOptions::new()
            .max_connections(1)
            .connect(&url)
            .await
            .map_err(|_| ())?;
        sqlx::migrate!("./migrations")
            .run(&pool)
            .await
            .map_err(|_| ())?;
        pool.close().await;
        Ok::<(), ()>(())
    }
    .await;
    if result.is_err() {
        eprintln!("Migration failed; verify the approved database and private database logs.");
        std::process::exit(1);
    }
    println!("Migrations completed.");
}
