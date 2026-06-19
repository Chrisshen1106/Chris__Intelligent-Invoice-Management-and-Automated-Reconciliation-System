# OCR Service

FastAPI service that accepts an uploaded image or PDF and runs PaddleOCR 3.5.0.
PDF uploads are rendered from the first page before OCR.

## Endpoints

- `GET /health`
- `POST /ocr` with multipart field `file`

## Configuration

- `PADDLEOCR_LANG`: OCR language, default `ch`
- `PADDLEOCR_DEVICE`: inference device, default `cpu`
- `PADDLEOCR_VERSION`: OCR model family, default `PP-OCRv5`

## Example

```sh
curl -F "file=@sample.png" http://localhost:8001/ocr
```
