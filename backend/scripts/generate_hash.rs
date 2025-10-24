// Quick script to generate bcrypt password hash
// Run with: cargo script generate_hash.rs

use bcrypt::{hash, DEFAULT_COST};

fn main() {
    let password = "Admin123!";
    let hash = hash(password, DEFAULT_COST).expect("Failed to hash password");
    println!("Password: {}", password);
    println!("Bcrypt Hash:\n{}", hash);
    println!("\nCopy this hash into the migration SQL file at line 225");
}
