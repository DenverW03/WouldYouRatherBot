use actix_web::{App, HttpServer};

mod rest_api;

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    // Exposing the REST API on the IP and port specified, just locall whilst in current early dev
    // stage
    HttpServer::new(|| {
        App::new()
            .service(rest_api::generate)
    })
    .bind(("127.0.0.1", 8080))?
    .run()
    .await
}
