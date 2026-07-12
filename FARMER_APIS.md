# Farmer APIs Documentation

This document explains all farmer-facing APIs with request and response examples for frontend integration (Android/Kotlin).

## Base Information

- Base URL: `http://localhost:8000`
- Auth type: Bearer JWT token
- Required header for protected APIs:

```http
Authorization: Bearer <access_token>
```

- Role required for all endpoints in this file: `farmer`

---

## 1. Register Farmer

### Endpoint

- Method: `POST`
- Path: `/farmer-register`
- Auth: Not required

### Request Body (JSON)

```json
{
  "username": "farmer_1",
  "password": "StrongPassword@123",
  "full_name": "Farmer One",
  "phone_number": "+919999999999"
}
```

### Notes

- `phone_number` is required for farmer registration.
- Username and phone number must be unique.

### Success Response

```json
{
  "username": "farmer_1",
  "full_name": "Farmer One",
  "role": "farmer",
  "disabled": false,
  "phone_number": "+919999999999"
}
```

### Error Response Examples

```json
{
  "detail": "Username already registered"
}
```

```json
{
  "detail": "Phone number is required for farmer registration"
}
```

---

## 2. Login (Farmer)

### Endpoint

- Method: `POST`
- Path: `/login`
- Auth: Not required

### Request Body (JSON)

```json
{
  "username": "farmer_1",
  "password": "StrongPassword@123"
}
```

### Success Response

```json
{
  "access_token": "<jwt_token>",
  "token_type": "bearer",
  "expires_in": 86400,
  "role": "farmer"
}
```

---

## 3. Create Pond (Geo-tagged)

Farmer must upload:
- Geo-tagged pond image
- Exact location (latitude and longitude)
- Pond name
- Total estimated area
- Fish species list

### Endpoint

- Method: `POST`
- Path: `/ponds`
- Auth: Required (`farmer` token)
- Content-Type: `multipart/form-data`

### Form Fields

- `name` (string, required): Pond name
- `latitude` (float, required): Latitude of pond location
- `longitude` (float, required): Longitude of pond location
- `estimated_area` (float, required): Estimated total area (numeric)
- `fish_species` (string, required): Either JSON array string OR comma-separated species
- `geo_image` (file, required): Geo-tagged image (`.jpg`, `.jpeg`, `.png`, `.bmp`, `.webp`)

### `fish_species` accepted formats

- JSON list string:

```text
["Rohu", "Catla", "Mrigal"]
```

- Comma-separated string:

```text
Rohu, Catla, Mrigal
```

### cURL Example

```bash
curl -X POST "http://localhost:8000/ponds" \
  -H "Authorization: Bearer <access_token>" \
  -F "name=Pond A" \
  -F "latitude=20.035725" \
  -F "longitude=73.852066" \
  -F "estimated_area=4500" \
  -F "fish_species=[\"Rohu\",\"Catla\"]" \
  -F "geo_image=@/path/to/pond.jpg"
```

### Success Response

```json
{
  "id": 1,
  "name": "Pond A",
  "latitude": 20.035725,
  "longitude": 73.852066,
  "estimated_area": 4500.0,
  "fish_species": ["Rohu", "Catla"],
  "verified": false,
  "created_at": "2026-07-09T10:20:30.120000",
  "image_url": "/ponds/1/image"
}
```

### Error Response Examples

```json
{
  "detail": "Invalid image type. Allowed: .bmp, .jpeg, .jpg, .png, .webp"
}
```

```json
{
  "detail": "fish_species must contain at least one species"
}
```

---

## 4. List All Ponds of Current Farmer

This returns pond history-style list (similar to consumer prediction history), including image URL.

### Endpoint

- Method: `GET`
- Path: `/ponds`
- Auth: Required (`farmer` token)

### Success Response

```json
[
  {
    "id": 1,
    "name": "Pond A",
    "latitude": 20.035725,
    "longitude": 73.852066,
    "estimated_area": 4500.0,
    "fish_species": ["Rohu", "Catla"],
    "verified": false,
    "created_at": "2026-07-09T10:20:30.120000",
    "image_url": "/ponds/1/image"
  },
  {
    "id": 2,
    "name": "Pond B",
    "latitude": 20.038101,
    "longitude": 73.850022,
    "estimated_area": 5000.0,
    "fish_species": ["Mrigal"],
    "verified": true,
    "created_at": "2026-07-08T08:10:22.540000",
    "image_url": "/ponds/2/image"
  }
]
```

---

## 5. Get Single Pond Detail

### Endpoint

- Method: `GET`
- Path: `/ponds/{pond_id}`
- Auth: Required (`farmer` token)

### Path Parameter

- `pond_id` (integer): Pond ID

### Success Response

```json
{
  "id": 1,
  "name": "Pond A",
  "latitude": 20.035725,
  "longitude": 73.852066,
  "estimated_area": 4500.0,
  "fish_species": ["Rohu", "Catla"],
  "verified": false,
  "created_at": "2026-07-09T10:20:30.120000",
  "image_url": "/ponds/1/image"
}
```

### Error Response

```json
{
  "detail": "Pond not found"
}
```

---

## 6. Get Pond Geo-tagged Image

### Endpoint

- Method: `GET`
- Path: `/ponds/{pond_id}/image`
- Auth: Required (`farmer` token)

### Path Parameter

- `pond_id` (integer): Pond ID

### Success Response

- Binary image stream
- Content-Type: from uploaded image (example: `image/jpeg`)

### Error Response Examples

```json
{
  "detail": "Pond not found"
}
```

```json
{
  "detail": "Pond image not found"
}
```

---

## 7. Farmer Reports APIs (Already Available)

As requested, reports APIs remain unchanged and continue to work.

### Existing report endpoints

- `POST /reports` (multipart) - Create report
- `GET /reports` - List own reports
- `GET /reports/{report_id}` - Report detail
- `GET /reports/{report_id}/photo` - Report image

Farmers can view report verification status but cannot verify reports themselves.

---

## Kotlin/Android Request Models (Recommended)

```kotlin
data class FarmerRegisterRequest(
    val username: String,
    val password: String,
    val full_name: String?,
    val phone_number: String
)

data class LoginRequest(
    val username: String,
    val password: String
)

data class TokenResponse(
    val access_token: String,
    val token_type: String,
    val expires_in: Int,
    val role: String
)

data class PondResponse(
    val id: Int,
    val name: String,
    val latitude: Double?,
    val longitude: Double?,
    val estimated_area: Double?,
    val fish_species: List<String>,
    val verified: Boolean,
    val created_at: String,
    val image_url: String?
)
```

## Kotlin Retrofit Interface Snippets

```kotlin
@Multipart
@POST("/ponds")
suspend fun createPond(
    @Part("name") name: RequestBody,
    @Part("latitude") latitude: RequestBody,
    @Part("longitude") longitude: RequestBody,
    @Part("estimated_area") estimatedArea: RequestBody,
    @Part("fish_species") fishSpecies: RequestBody,
    @Part geoImage: MultipartBody.Part,
    @Header("Authorization") bearerToken: String
): Response<PondResponse>

@GET("/ponds")
suspend fun listPonds(
    @Header("Authorization") bearerToken: String
): Response<List<PondResponse>>

@GET("/ponds/{pond_id}")
suspend fun getPondDetail(
    @Path("pond_id") pondId: Int,
    @Header("Authorization") bearerToken: String
): Response<PondResponse>

@GET("/ponds/{pond_id}/image")
suspend fun getPondImage(
    @Path("pond_id") pondId: Int,
    @Header("Authorization") bearerToken: String
): Response<ResponseBody>
```

---

## Validation + Access Rules Summary

- Only farmer can access `/ponds*` farmer endpoints.
- Farmer sees only their own ponds.
- Pond image must be one of: `.jpg`, `.jpeg`, `.png`, `.bmp`, `.webp`.
- `fish_species` must contain at least one species.
- `latitude`, `longitude`, `estimated_area`, and `geo_image` are required at creation time.

---

## Quick Test Sequence

1. Register farmer using `/farmer-register`
2. Login via `/login` and store token
3. Create pond with multipart data and geo image
4. Call `/ponds` to list all own ponds
5. Call `/ponds/{pond_id}` for details
6. Load image from `/ponds/{pond_id}/image`
