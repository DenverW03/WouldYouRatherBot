use actix_web::{post, web, Responder, HttpResponse};
use actix_multipart::form::{tempfile::TempFile, MultipartForm};
use std::io::Error;

// As video file is constructed of two images and some text have to receive images together
#[derive(Debug, MultipartForm)]
pub struct UploadForm {
    #[multipart(limit = "100MB")]
    upper_image: TempFile,
    lower_image: TempFile,
}

// Each request will have a unique string url structured as: upper_string+lower_string+userID then
// images are received in the UploadForm multipart form
#[post("/generate/{unique_str:.+}")]
async fn generate(
    user_id: web::Path<String>,
    MultipartForm(form): MultipartForm<UploadForm>,
    ) -> Result<impl Responder, Error> {


    Ok(HttpResponse::Ok())
}
