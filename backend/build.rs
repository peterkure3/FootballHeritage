fn main() {
    // SQLx embeds the migration list at compile time; track newly added files too.
    println!("cargo:rerun-if-changed=migrations");
}
