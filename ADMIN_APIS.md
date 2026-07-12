# Admin APIs Documentation

This document describes all admin-facing APIs in the FastAPI backend and is intended for Android/Kotlin frontend implementation.

## Base Information

- **Base URL:** `http://localhost:8000`
- **Authentication:** JWT Bearer token
- **Role required:** `admin`
- **Header for protected routes:**

```http
Authorization: Bearer <access_token>
```

---

## Authentication Flow

Admin users authenticate the same way as other roles:

1. Register an admin account using `/admin-register`
2. Login using `/login`
3. Save `access_token` locally
4. Send the token in the `Authorization` header for all admin routes
5. Use `/logout` to revoke the token

The login response includes the user role as a string:

```json
{
  "access_token": "<jwt_token>",
  "token_type": "bearer",
  "expires_in": 86400,
  "role": "admin"
}
```

---

## Common Response Models

### UserResponse
Used by registration endpoints.

```json
{
  "username": "admin_1",
  "full_name": "Main Admin",
  "role": "admin",
  "disabled": false,
  "phone_number": "+919999999999"
}
```

### AdminPondResponse
Used by pond listing endpoints.

```json
{
  "id": 1,
  "name": "Pond A",
  "latitude": 20.035725,
  "longitude": 73.852066,
  "estimated_area": 4500.0,
  "fish_species": ["Rohu", "Catla"],
  "verified": false,
  "created_at": "2026-07-12T10:20:30.120000",
  "image_url": "/admin/ponds/1/image",
  "owner_username": "farmer_john",
  "owner_phone": "+919999999999"
}
```

### AdminReportResponse
Used by report listing endpoints.

```json
{
  "id": 10,
  "report_name": "Disease Alert",
  "symptoms": "Fish are swimming slowly and have white marks",
  "pond_id": 1,
  "pond_name": "Pond A",
  "created_at": "2026-07-12T11:15:45.440000",
  "photo_url": "/admin/reports/10/photo",
  "verified": false,
  "farmer_username": "farmer_john",
  "farmer_phone": "+919999999999"
}
```

---

## 1. Register Admin

### Endpoint

- **Method:** `POST`
- **Path:** `/admin-register`
- **Auth:** Not required

### Request Body

```json
{
  "username": "admin_1",
  "password": "StrongPassword@123",
  "full_name": "Main Admin",
  "phone_number": "+919999999999"
}
```

### Field Notes

- `username` is required and must be unique
- `password` is required
- `full_name` is optional; if omitted, username is used
- `phone_number` is optional for admin registration
- If `phone_number` is provided, it must be unique

### Success Response

```json
{
  "username": "admin_1",
  "full_name": "Main Admin",
  "role": "admin",
  "disabled": false,
  "phone_number": "+919999999999"
}
```

### Error Responses

```json
{
  "detail": "Username already registered"
}
```

```json
{
  "detail": "Phone number already registered"
}
```

### Kotlin Example

```kotlin
data class AdminRegisterRequest(
    val username: String,
    val password: String,
    val full_name: String?,
    val phone_number: String?
)

data class UserResponse(
    val username: String,
    val full_name: String,
    val role: String,
    val disabled: Boolean,
    val phone_number: String?
)

interface ApiService {
    @POST("/admin-register")
    suspend fun registerAdmin(
        @Body request: AdminRegisterRequest
    ): Response<UserResponse>
}
```

---

## 2. Login

### Endpoint

- **Method:** `POST`
- **Path:** `/login`
- **Auth:** Not required

### Request Body

```json
{
  "username": "admin_1",
  "password": "StrongPassword@123"
}
```

### Success Response

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 86400,
  "role": "admin"
}
```

### Error Responses

```json
{
  "detail": "Incorrect username or password"
}
```

```json
{
  "detail": "Inactive user"
}
```

### Kotlin Example

```kotlin
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

interface ApiService {
    @POST("/login")
    suspend fun login(@Body request: LoginRequest): Response<TokenResponse>
}
```

### Token Storage Tip

Use `expires_in` to auto-logout locally after expiry.

```kotlin
val expiryTime = System.currentTimeMillis() + (tokenResponse.expires_in * 1000L)
```

---

## 3. Logout

### Endpoint

- **Method:** `POST`
- **Path:** `/logout`
- **Auth:** Required

### Request Header

```http
Authorization: Bearer <access_token>
```

### Success Response

```json
{
  "detail": "Successfully logged out"
}
```

### Kotlin Example

```kotlin
interface ApiService {
    @POST("/logout")
    suspend fun logout(
        @Header("Authorization") bearerToken: String
    ): Response<Map<String, String>>
}
```

---

## 4. View All Ponds

This endpoint is for admin moderation of farmer ponds.

### Endpoint

- **Method:** `GET`
- **Path:** `/admin/ponds`
- **Auth:** Required

### Sorting Rule

- Unverified ponds appear first
- Verified ponds appear after pending ones
- Inside each group, newer ponds appear first

### Success Response

```json
[
  {
    "id": 3,
    "name": "Pending Pond",
    "latitude": 20.035725,
    "longitude": 73.852066,
    "estimated_area": 2200.0,
    "fish_species": ["Rohu", "Catla"],
    "verified": false,
    "created_at": "2026-07-12T11:45:30.000000",
    "image_url": "/admin/ponds/3/image",
    "owner_username": "farmer_john",
    "owner_phone": "+919999999999"
  },
  {
    "id": 1,
    "name": "Verified Pond",
    "latitude": 20.038101,
    "longitude": 73.850022,
    "estimated_area": 5000.0,
    "fish_species": ["Mrigal"],
    "verified": true,
    "created_at": "2026-07-11T08:15:30.000000",
    "image_url": "/admin/ponds/1/image",
    "owner_username": "farmer_jane",
    "owner_phone": "+919888888888"
  }
]
```

### Kotlin Example

```kotlin
data class AdminPondResponse(
    val id: Int,
    val name: String,
    val latitude: Double?,
    val longitude: Double?,
    val estimated_area: Double?,
    val fish_species: List<String>,
    val verified: Boolean,
    val created_at: String,
    val image_url: String?,
    val owner_username: String,
    val owner_phone: String?
)

interface ApiService {
    @GET("/admin/ponds")
    suspend fun getAllPonds(
        @Header("Authorization") bearerToken: String
    ): Response<List<AdminPondResponse>>
}
```

---

## 5. View Pond Geo-Tagged Image

### Endpoint

- **Method:** `GET`
- **Path:** `/admin/ponds/{pond_id}/image`
- **Auth:** Required

### Path Parameter

- `pond_id`: ID of the pond

### Success Response

- Binary image stream
- Content-Type: usually `image/jpeg` or `image/png`

### Error Responses

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

### Kotlin Example

```kotlin
interface ApiService {
    @GET("/admin/ponds/{pond_id}/image")
    suspend fun getPondImage(
        @Path("pond_id") pondId: Int,
        @Header("Authorization") bearerToken: String
    ): Response<ResponseBody>
}
```

---

## 6. Verify or Unverify Pond

### Endpoint

- **Method:** `PATCH`
- **Path:** `/admin/ponds/{pond_id}/verify`
- **Auth:** Required

### Query Parameter

- `verified` (boolean): `true` or `false`

### Example Requests

```http
PATCH /admin/ponds/3/verify?verified=true
```

```http
PATCH /admin/ponds/3/verify?verified=false
```

### Success Response

```json
{
  "id": 3,
  "verified": true
}
```

### Notes

- Admin can both verify and unverify a pond
- Farmers will see the updated verification state in their own pond list

### Kotlin Example

```kotlin
interface ApiService {
    @PATCH("/admin/ponds/{pond_id}/verify")
    suspend fun verifyPond(
        @Path("pond_id") pondId: Int,
        @Query("verified") verified: Boolean,
        @Header("Authorization") bearerToken: String
    ): Response<Map<String, Any>>
}
```

---

## 7. View All Reports

This endpoint is for admin moderation of farmer-submitted reports.

### Endpoint

- **Method:** `GET`
- **Path:** `/admin/reports`
- **Auth:** Required

### Sorting Rule

- Unverified reports appear first
- Verified reports appear after pending ones
- Inside each group, newer reports appear first

### Success Response

```json
[
  {
    "id": 10,
    "report_name": "Disease Alert",
    "symptoms": "Fish are swimming slowly and have white marks",
    "pond_id": 1,
    "pond_name": "Pond A",
    "created_at": "2026-07-12T11:15:45.440000",
    "photo_url": "/admin/reports/10/photo",
    "verified": false,
    "farmer_username": "farmer_john",
    "farmer_phone": "+919999999999"
  },
  {
    "id": 8,
    "report_name": "Weekly Check",
    "symptoms": "Normal water behavior",
    "pond_id": 1,
    "pond_name": "Pond A",
    "created_at": "2026-07-11T09:10:11.000000",
    "photo_url": "/admin/reports/8/photo",
    "verified": true,
    "farmer_username": "farmer_john",
    "farmer_phone": "+919999999999"
  }
]
```

### Important Fields

- `farmer_phone` is included so admin can contact the farmer directly
- `pond_name` identifies which pond the report belongs to
- `photo_url` points to the admin-only report photo route

### Kotlin Example

```kotlin
data class AdminReportResponse(
    val id: Int,
    val report_name: String,
    val symptoms: String,
    val pond_id: Int,
    val pond_name: String,
    val created_at: String,
    val photo_url: String,
    val verified: Boolean,
    val farmer_username: String,
    val farmer_phone: String?
)

interface ApiService {
    @GET("/admin/reports")
    suspend fun getAllReports(
        @Header("Authorization") bearerToken: String
    ): Response<List<AdminReportResponse>>
}
```

---

## 8. View Report Photo

### Endpoint

- **Method:** `GET`
- **Path:** `/admin/reports/{report_id}/photo`
- **Auth:** Required

### Path Parameter

- `report_id`: ID of the report

### Success Response

- Binary image stream
- Content-Type: usually `image/jpeg` or `image/png`

### Error Responses

```json
{
  "detail": "Report not found"
}
```

```json
{
  "detail": "Report photo not found"
}
```

### Kotlin Example

```kotlin
interface ApiService {
    @GET("/admin/reports/{report_id}/photo")
    suspend fun getReportPhoto(
        @Path("report_id") reportId: Int,
        @Header("Authorization") bearerToken: String
    ): Response<ResponseBody>
}
```

---

## 9. Verify or Unverify Report

### Endpoint

- **Method:** `PATCH`
- **Path:** `/admin/reports/{report_id}/verify`
- **Auth:** Required

### Query Parameter

- `verified` (boolean): `true` or `false`

### Example Requests

```http
PATCH /admin/reports/10/verify?verified=true
```

```http
PATCH /admin/reports/10/verify?verified=false
```

### Success Response

```json
{
  "id": 10,
  "verified": true
}
```

### Notes

- Only admin can change report verification status
- Farmers can only view the verification result for their own reports

### Kotlin Example

```kotlin
interface ApiService {
    @PATCH("/admin/reports/{report_id}/verify")
    suspend fun verifyReport(
        @Path("report_id") reportId: Int,
        @Query("verified") verified: Boolean,
        @Header("Authorization") bearerToken: String
    ): Response<Map<String, Any>>
}
```

---

## Admin Access Rules

- Admin users can register using `/admin-register`
- Admin users can login using `/login`
- Admin users can logout using `/logout`
- Admin can view all ponds and reports
- Admin can verify/unverify ponds and reports
- Admin can view farmer phone numbers for contact
- Admin sees pending ponds/reports first

---

## Kotlin Request/Response Models

```kotlin
data class AdminRegisterRequest(
    val username: String,
    val password: String,
    val full_name: String?,
    val phone_number: String?
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

data class AdminPondResponse(
    val id: Int,
    val name: String,
    val latitude: Double?,
    val longitude: Double?,
    val estimated_area: Double?,
    val fish_species: List<String>,
    val verified: Boolean,
    val created_at: String,
    val image_url: String?,
    val owner_username: String,
    val owner_phone: String?
)

data class AdminReportResponse(
    val id: Int,
    val report_name: String,
    val symptoms: String,
    val pond_id: Int,
    val pond_name: String,
    val created_at: String,
    val photo_url: String,
    val verified: Boolean,
    val farmer_username: String,
    val farmer_phone: String?
)
```

---

## Quick Retrofit Setup Example

```kotlin
interface ApiService {
    @POST("/admin-register")
    suspend fun registerAdmin(@Body request: AdminRegisterRequest): Response<UserResponse>

    @POST("/login")
    suspend fun login(@Body request: LoginRequest): Response<TokenResponse>

    @POST("/logout")
    suspend fun logout(@Header("Authorization") bearerToken: String): Response<Map<String, String>>

    @GET("/admin/ponds")
    suspend fun getAllPonds(@Header("Authorization") bearerToken: String): Response<List<AdminPondResponse>>

    @PATCH("/admin/ponds/{pond_id}/verify")
    suspend fun verifyPond(
        @Path("pond_id") pondId: Int,
        @Query("verified") verified: Boolean,
        @Header("Authorization") bearerToken: String
    ): Response<Map<String, Any>>

    @GET("/admin/ponds/{pond_id}/image")
    suspend fun getPondImage(
        @Path("pond_id") pondId: Int,
        @Header("Authorization") bearerToken: String
    ): Response<ResponseBody>

    @GET("/admin/reports")
    suspend fun getAllReports(@Header("Authorization") bearerToken: String): Response<List<AdminReportResponse>>

    @PATCH("/admin/reports/{report_id}/verify")
    suspend fun verifyReport(
        @Path("report_id") reportId: Int,
        @Query("verified") verified: Boolean,
        @Header("Authorization") bearerToken: String
    ): Response<Map<String, Any>>

    @GET("/admin/reports/{report_id}/photo")
    suspend fun getReportPhoto(
        @Path("report_id") reportId: Int,
        @Header("Authorization") bearerToken: String
    ): Response<ResponseBody>
}
```

---

## Expected UI Behavior

- Show admin dashboard after successful login
- List ponds with unverified items first
- List reports with unverified items first
- Provide approve/reject buttons for each pond/report
- Show farmer phone number on admin list screens for contact
- Open pond/report images in a preview screen

---

## Summary of Admin Endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | `/admin-register` | Create admin account |
| POST | `/login` | Login and get JWT token |
| POST | `/logout` | Revoke token |
| GET | `/admin/ponds` | List all ponds, pending first |
| GET | `/admin/ponds/{pond_id}/image` | Download pond geo-tagged image |
| PATCH | `/admin/ponds/{pond_id}/verify` | Verify/unverify pond |
| GET | `/admin/reports` | List all reports, pending first |
| GET | `/admin/reports/{report_id}/photo` | Download report photo |
| PATCH | `/admin/reports/{report_id}/verify` | Verify/unverify report |

---

**Last Updated:** July 12, 2026
