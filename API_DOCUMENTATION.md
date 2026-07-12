# 🐟 Fish Species Detection API - Complete Documentation

**Version:** 1.0.0  
**Base URL:** `http://localhost:8000` (development) or your production server  
**Authentication:** JWT Bearer Token (Bearer schema)

---

## Table of Contents

1. [Authentication Flow](#authentication-flow)
2. [Base Response Format](#base-response-format)
3. [Error Handling](#error-handling)
4. [Authentication Endpoints](#authentication-endpoints)
5. [Consumer Endpoints](#consumer-endpoints)
6. [Farmer Endpoints](#farmer-endpoints)
7. [Admin Endpoints](#admin-endpoints)
8. [Health & Status Endpoints](#health--status-endpoints)
9. [Common Status Codes](#common-status-codes)

---

## Authentication Flow

### Overview
The API uses JWT (JSON Web Token) based authentication with Bearer tokens.

### Token Lifecycle
1. User registers (`/consumer-register`, `/farmer-register`, `/admin-register`)
2. User logs in (`/login` or `/token`) to get JWT token
3. User includes token in `Authorization: Bearer {token}` header for protected endpoints
4. Token expires after configured time (default: 1440 minutes = 24 hours)
5. User calls `/logout` to revoke token immediately

### Token Expiry
- **Expires In:** 1440 minutes (24 hours) by default
- **Refresh:** Must login again after expiry
- **Early Revocation:** Call `/logout` endpoint

### Kotlin Implementation Example
```kotlin
// Store token after login
val token = loginResponse.access_token
val preferences = getSharedPreferences("auth", Context.MODE_PRIVATE)
preferences.edit().putString("jwt_token", token).apply()

// Add to all requests
val token = preferences.getString("jwt_token", "")
request.addHeader("Authorization", "Bearer $token")

// Check expiry before request
val expiresIn = loginResponse.expires_in // in seconds
val expiryTime = System.currentTimeMillis() + (expiresIn * 1000)
preferences.edit().putLong("token_expiry", expiryTime).apply()
```

---

## Base Response Format

### Success Response
```json
{
  "success": true,
  "data": {},
  "message": "Operation successful"
}
```

### Error Response
```json
{
  "success": false,
  "error": "Error code or message",
  "details": "Detailed error description"
}
```

---

## Error Handling

### HTTP Status Codes Returned
- **200 OK** - Request successful
- **201 Created** - Resource created
- **400 Bad Request** - Invalid input/validation error
- **401 Unauthorized** - Invalid/missing token or invalid credentials
- **403 Forbidden** - User doesn't have permission (wrong role)
- **404 Not Found** - Resource not found
- **500 Internal Server Error** - Server error

### Kotlin Error Handling Example
```kotlin
try {
    val response = apiService.predictFish(file, token)
    if (response.isSuccessful) {
        val prediction = response.body()
        // Handle success
    } else {
        when (response.code()) {
            401 -> handleUnauthorized() // Token expired/invalid
            403 -> handleForbidden()    // Wrong role
            404 -> handleNotFound()     // Resource doesn't exist
            else -> handleError(response.errorBody()?.string())
        }
    }
} catch (e: Exception) {
    handleNetworkError(e)
}
```

---

## Authentication Endpoints

### 1. Register Consumer (Public)

**Endpoint:** `POST /consumer-register`

**Access:** Public (No token required)

**Request Body:**
```json
{
  "username": "john_consumer",
  "password": "securePassword123",
  "full_name": "John Doe",
  "phone_number": "+1234567890"
}
```

**Response (200 OK):**
```json
{
  "username": "john_consumer",
  "full_name": "John Doe",
  "role": "consumer",
  "disabled": false,
  "phone_number": "+1234567890"
}
```

**Error Cases:**
- `400 Bad Request` - Username already registered
- `400 Bad Request` - Phone number already registered

**Kotlin Implementation:**
```kotlin
data class ConsumerRegisterRequest(
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
    @POST("/consumer-register")
    suspend fun registerConsumer(
        @Body request: ConsumerRegisterRequest
    ): Response<UserResponse>
}

// Usage
val request = ConsumerRegisterRequest(
    username = "john_consumer",
    password = "securePassword123",
    full_name = "John Doe",
    phone_number = "+1234567890"
)
val response = apiService.registerConsumer(request)
```

---

### 2. Register Farmer (Public)

**Endpoint:** `POST /farmer-register`

**Access:** Public (No token required)

**Request Body:**
```json
{
  "username": "farmer_john",
  "password": "securePassword123",
  "full_name": "John Farmer",
  "phone_number": "+1234567890"
}
```

**Response (200 OK):**
```json
{
  "username": "farmer_john",
  "full_name": "John Farmer",
  "role": "farmer",
  "disabled": false,
  "phone_number": "+1234567890"
}
```

**Error Cases:**
- `400 Bad Request` - Username already registered
- `400 Bad Request` - Phone number already registered
- `400 Bad Request` - Phone number is required

**Note:** Phone number is REQUIRED for farmer registration.

**Kotlin Implementation:**
```kotlin
data class FarmerRegisterRequest(
    val username: String,
    val password: String,
    val full_name: String?,
    val phone_number: String  // REQUIRED
)

interface ApiService {
    @POST("/farmer-register")
    suspend fun registerFarmer(
        @Body request: FarmerRegisterRequest
    ): Response<UserResponse>
}

// Usage
val request = FarmerRegisterRequest(
    username = "farmer_john",
    password = "securePassword123",
    full_name = "John Farmer",
    phone_number = "+1234567890"  // Must not be null
)
val response = apiService.registerFarmer(request)
```

---

### 3. Register Admin (Public)

**Endpoint:** `POST /admin-register`

**Access:** Public (No token required)

**Request Body:**
```json
{
  "username": "admin_user",
  "password": "securePassword123",
  "full_name": "Admin Name",
  "phone_number": "+1234567890"
}
```

**Response (200 OK):**
```json
{
  "username": "admin_user",
  "full_name": "Admin Name",
  "role": "admin",
  "disabled": false,
  "phone_number": "+1234567890"
}
```

**Error Cases:**
- `400 Bad Request` - Username already registered
- `400 Bad Request` - Phone number already registered

**Kotlin Implementation:**
```kotlin
interface ApiService {
    @POST("/admin-register")
    suspend fun registerAdmin(
        @Body request: FarmerRegisterRequest
    ): Response<UserResponse>
}
```

---

### 4. Login (Public)

**Endpoint:** `POST /login`

**Access:** Public (No token required)

**Request Body:**
```json
{
  "username": "john_consumer",
  "password": "securePassword123"
}
```

**Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 86400,
  "role": "consumer"
}
```

**Error Cases:**
- `401 Unauthorized` - Incorrect username or password
- `403 Forbidden` - User account disabled

**Expires In:** In seconds (86400 = 24 hours)

**Kotlin Implementation:**
```kotlin
data class LoginRequest(
    val username: String,
    val password: String
)

data class TokenResponse(
    val access_token: String,
    val token_type: String,
    val expires_in: Int, // in seconds
    val role: String
)

interface ApiService {
    @POST("/login")
    suspend fun login(@Body request: LoginRequest): Response<TokenResponse>
}

// Usage
val response = apiService.login(LoginRequest("john_consumer", "password123"))
if (response.isSuccessful) {
    val token = response.body()?.access_token
    val expiresIn = response.body()?.expires_in ?: 86400
    
    // Save token
    saveTokenToPreferences(token, expiresIn)
}
```

---

### 5. Logout (Protected)

**Endpoint:** `POST /logout`

**Access:** All authenticated users (Consumer, Farmer, Admin)

**Headers Required:**
```
Authorization: Bearer {token}
```

**Response (200 OK):**
```json
{
  "detail": "Successfully logged out"
}
```

**Error Cases:**
- `401 Unauthorized` - Token invalid or expired
- `400 Bad Request` - Invalid token payload

**Kotlin Implementation:**
```kotlin
interface ApiService {
    @POST("/logout")
    suspend fun logout(
        @Header("Authorization") bearerToken: String
    ): Response<Map<String, String>>
}

// Usage
val token = getTokenFromPreferences()
val response = apiService.logout("Bearer $token")
if (response.isSuccessful) {
    clearPreferences()  // Clear local token storage
}
```

---

## Consumer Endpoints

### 1. Predict Fish Species from Image

**Endpoint:** `POST /predict`

**Access:** Consumer role only (requires valid JWT token)

**Headers Required:**
```
Authorization: Bearer {token}
Content-Type: multipart/form-data
```

**Request:**
- **file** (required): Image file (JPG, PNG, BMP, WebP)
  - Max recommended: 5MB
  - Supported formats: `.jpg`, `.jpeg`, `.png`, `.bmp`, `.webp`

**Response (200 OK):**
```json
{
  "success": true,
  "species": "Rohu",
  "species_confidence": 0.95,
  "species_confidence_percent": "95.0%",
  "disease_status": "HEALTHY",
  "disease_confidence": 0.87,
  "disease_confidence_percent": "87.0%",
  "yolo_confidence": 0.92,
  "yolo_confidence_percent": "92.0%",
  "is_valid_detection": true,
  "all_class_probabilities": [
    {
      "class_name": "Catla",
      "probability": 0.05,
      "confidence_percent": "5.0%"
    },
    {
      "class_name": "CommonCarp",
      "probability": 0.02,
      "confidence_percent": "2.0%"
    },
    {
      "class_name": "Mori",
      "probability": 0.01,
      "confidence_percent": "1.0%"
    },
    {
      "class_name": "Rohu",
      "probability": 0.95,
      "confidence_percent": "95.0%"
    },
    {
      "class_name": "SilverCarp",
      "probability": 0.02,
      "confidence_percent": "2.0%"
    }
  ],
  "message": "Fish detected and classified successfully",
  "detection_count": 1,
  "prediction_id": 42
}
```

**Error Cases:**
- `401 Unauthorized` - Token missing/invalid
- `403 Forbidden` - User is not a consumer
- `400 Bad Request` - Invalid file type or empty file
- `503 Service Unavailable` - Models not loaded

**Three-Stage Pipeline:**
1. **YOLO Detection** - Locates fish in image
2. **EfficientNet Classification** - Classifies fish species
3. **SavedModel Disease Detection** - Determines health status

**Supported Species:**
- Catla
- CommonCarp
- Mori
- Rohu
- SilverCarp

**Kotlin Implementation:**
```kotlin
data class ClassProbability(
    val class_name: String,
    val probability: Double,
    val confidence_percent: String
)

data class PredictionResult(
    val success: Boolean,
    val species: String,
    val species_confidence: Double,
    val species_confidence_percent: String,
    val disease_status: String,
    val disease_confidence: Double,
    val disease_confidence_percent: String,
    val yolo_confidence: Double,
    val yolo_confidence_percent: String,
    val is_valid_detection: Boolean,
    val all_class_probabilities: List<ClassProbability>,
    val message: String,
    val detection_count: Int,
    val prediction_id: Int
)

interface ApiService {
    @Multipart
    @POST("/predict")
    suspend fun predictFish(
        @Part file: MultipartBody.Part,
        @Header("Authorization") bearerToken: String
    ): Response<PredictionResult>
}

// Usage
val file = File(imageFilePath)
val requestFile = RequestBody.create("image/jpeg".toMediaType(), file)
val body = MultipartBody.Part.createFormData("file", file.name, requestFile)
val token = getTokenFromPreferences()

val response = apiService.predictFish(body, "Bearer $token")
if (response.isSuccessful) {
    val prediction = response.body()
    Log.d("Prediction", "Species: ${prediction?.species}")
    Log.d("Prediction", "Health: ${prediction?.disease_status}")
}
```

---

### 2. Batch Predict (Multiple Images)

**Endpoint:** `POST /predict-batch`

**Access:** Consumer role only

**Headers Required:**
```
Authorization: Bearer {token}
Content-Type: multipart/form-data
```

**Request:**
- **files** (required): Array of image files (max 10 images)

**Response (200 OK):**
```json
{
  "batch_size": 2,
  "results": [
    {
      "filename": "fish1.jpg",
      "prediction": {
        "success": true,
        "species": "Rohu",
        "species_confidence": 0.95,
        ...
      }
    },
    {
      "filename": "fish2.jpg",
      "prediction": {
        "success": true,
        "species": "Catla",
        "species_confidence": 0.88,
        ...
      }
    }
  ]
}
```

**Error Cases:**
- `401 Unauthorized` - Token missing/invalid
- `403 Forbidden` - User is not a consumer
- `400 Bad Request` - More than 10 images

**Kotlin Implementation:**
```kotlin
interface ApiService {
    @Multipart
    @POST("/predict-batch")
    suspend fun predictBatch(
        @Part files: List<MultipartBody.Part>,
        @Header("Authorization") bearerToken: String
    ): Response<BatchPredictionResponse>
}

// Usage
val files = mutableListOf<MultipartBody.Part>()
imageFiles.forEach { file ->
    val requestFile = RequestBody.create("image/jpeg".toMediaType(), file)
    files.add(MultipartBody.Part.createFormData("files", file.name, requestFile))
}

val response = apiService.predictBatch(files, "Bearer $token")
```

---

### 3. Get Prediction History

**Endpoint:** `GET /predictions`

**Access:** Consumer role only

**Headers Required:**
```
Authorization: Bearer {token}
```

**Response (200 OK):**
```json
[
  {
    "id": 42,
    "filename": "fish_photo.jpg",
    "species": "Rohu",
    "species_confidence": 0.95,
    "species_confidence_percent": "95.0%",
    "yolo_confidence": 0.92,
    "yolo_confidence_percent": "92.0%",
    "is_valid_detection": true,
    "all_class_probabilities": [...],
    "disease_status": "HEALTHY",
    "disease_confidence": 0.87,
    "disease_confidence_percent": "87.0%",
    "message": "Fish detected and classified successfully",
    "detection_count": 1,
    "created_at": "2026-05-18T10:30:45.123456",
    "image_url": "/predictions/42/image"
  }
]
```

**Kotlin Implementation:**
```kotlin
data class PredictionHistoryItem(
    val id: Int,
    val filename: String,
    val species: String,
    val species_confidence: Double,
    val species_confidence_percent: String,
    val yolo_confidence: Double,
    val yolo_confidence_percent: String,
    val is_valid_detection: Boolean,
    val all_class_probabilities: List<ClassProbability>,
    val disease_status: String,
    val disease_confidence: Double,
    val disease_confidence_percent: String,
    val message: String,
    val detection_count: Int,
    val created_at: String,
    val image_url: String
)

interface ApiService {
    @GET("/predictions")
    suspend fun getPredictionHistory(
        @Header("Authorization") bearerToken: String
    ): Response<List<PredictionHistoryItem>>
}

// Usage
val response = apiService.getPredictionHistory("Bearer $token")
if (response.isSuccessful) {
    val history = response.body() ?: emptyList()
    history.forEach { prediction ->
        Log.d("History", "${prediction.filename}: ${prediction.species}")
    }
}
```

---

### 4. Get Single Prediction Detail

**Endpoint:** `GET /predictions/{prediction_id}`

**Access:** Consumer role only (can only view own predictions)

**Headers Required:**
```
Authorization: Bearer {token}
```

**Path Parameters:**
- `prediction_id` (required): ID of the prediction to retrieve

**Response (200 OK):**
Same as single item in prediction history response

**Error Cases:**
- `401 Unauthorized` - Token invalid
- `403 Forbidden` - Not a consumer
- `404 Not Found` - Prediction not found or doesn't belong to user

**Kotlin Implementation:**
```kotlin
interface ApiService {
    @GET("/predictions/{prediction_id}")
    suspend fun getPredictionDetail(
        @Path("prediction_id") predictionId: Int,
        @Header("Authorization") bearerToken: String
    ): Response<PredictionHistoryItem>
}
```

---

### 5. Download Prediction Image

**Endpoint:** `GET /predictions/{prediction_id}/image`

**Access:** Consumer role only

**Headers Required:**
```
Authorization: Bearer {token}
Accept: image/*
```

**Response (200 OK):**
- Binary image data
- Content-Type: Based on original image format

**Error Cases:**
- `401 Unauthorized` - Token invalid
- `404 Not Found` - Prediction not found

**Kotlin Implementation:**
```kotlin
interface ApiService {
    @GET("/predictions/{prediction_id}/image")
    suspend fun getPredictionImage(
        @Path("prediction_id") predictionId: Int,
        @Header("Authorization") bearerToken: String
    ): Response<ResponseBody>
}

// Usage
val response = apiService.getPredictionImage(42, "Bearer $token")
if (response.isSuccessful) {
    val bitmap = BitmapFactory.decodeStream(response.body()?.byteStream())
    imageView.setImageBitmap(bitmap)
}
```

---

## Farmer Endpoints

### 1. Create Pond

**Endpoint:** `POST /ponds`

**Access:** Farmer role only

**Headers Required:**
```
Authorization: Bearer {token}
Content-Type: multipart/form-data
```

**Request (form-data):**
- `name` (string, required)
- `latitude` (float, required)
- `longitude` (float, required)
- `estimated_area` (float, required)
- `fish_species` (string, required: JSON array string or comma separated)
- `geo_image` (file, required)

**Response (200 OK):**
```json
{
  "id": 1,
  "name": "Pond A",
    "latitude": 20.035725,
    "longitude": 73.852066,
    "estimated_area": 5000.0,
    "fish_species": ["Rohu", "Catla"],
  "verified": false,
    "created_at": "2026-05-18T10:30:45.123456",
    "image_url": "/ponds/1/image"
}
```

**Error Cases:**
- `401 Unauthorized` - Token invalid
- `403 Forbidden` - User is not a farmer

**Kotlin Implementation:**
```kotlin
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

interface ApiService {
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
}

// Usage
val response = apiService.createPond(
    name = RequestBody.create("text/plain".toMediaType(), "Pond A"),
    latitude = RequestBody.create("text/plain".toMediaType(), "20.035725"),
    longitude = RequestBody.create("text/plain".toMediaType(), "73.852066"),
    estimatedArea = RequestBody.create("text/plain".toMediaType(), "5000"),
    fishSpecies = RequestBody.create("text/plain".toMediaType(), "[\"Rohu\",\"Catla\"]"),
    geoImage = photoPart,
    bearerToken = "Bearer $token"
)
```

---

### 2. List Farmer's Ponds

**Endpoint:** `GET /ponds`

**Access:** Farmer role only

**Headers Required:**
```
Authorization: Bearer {token}
```

**Response (200 OK):**
```json
[
  {
    "id": 1,
    "name": "Pond A",
        "latitude": 20.035725,
        "longitude": 73.852066,
        "estimated_area": 5000.0,
        "fish_species": ["Rohu", "Catla"],
    "verified": false,
        "created_at": "2026-05-18T10:30:45.123456",
        "image_url": "/ponds/1/image"
  },
  {
    "id": 2,
    "name": "Pond B",
        "latitude": 20.039999,
        "longitude": 73.859999,
        "estimated_area": 3000.0,
        "fish_species": ["Mori"],
    "verified": true,
        "created_at": "2026-05-17T08:15:30.123456",
        "image_url": "/ponds/2/image"
  }
]
```

**Kotlin Implementation:**
```kotlin
interface ApiService {
    @GET("/ponds")
    suspend fun listPonds(
        @Header("Authorization") bearerToken: String
    ): Response<List<PondResponse>>
}

// Usage
val response = apiService.listPonds("Bearer $token")
if (response.isSuccessful) {
    val ponds = response.body() ?: emptyList()
    ponds.forEach { pond ->
        Log.d("Ponds", "Pond: ${pond.name}, Verified: ${pond.verified}")
    }
}
```

---

### 3. Create Report

**Endpoint:** `POST /reports`

**Access:** Farmer role only

**Headers Required:**
```
Authorization: Bearer {token}
Content-Type: multipart/form-data
```

**Request:**
- **pond_name** (required, form): Name of the pond
- **report_name** (required, form): Name/title for the report
- **symptoms** (required, form): Description of symptoms observed
- **photo** (required, file): Photo of the fish/pond issue

**Response (200 OK):**
```json
{
  "id": 1,
  "report_name": "Fish Disease Report",
  "symptoms": "White spots on gills and body",
  "pond_id": 1,
  "pond_name": "Pond A",
  "created_at": "2026-05-18T10:30:45.123456",
  "verified": false,
  "photo_url": "/reports/1/photo"
}
```

**Error Cases:**
- `401 Unauthorized` - Token invalid
- `403 Forbidden` - User is not a farmer
- `404 Not Found` - Pond not found for this farmer
- `400 Bad Request` - Invalid photo type

**Kotlin Implementation:**
```kotlin
data class ReportCreateRequest(
    val pond_name: String,
    val report_name: String,
    val symptoms: String
    // photo sent as multipart
)

data class ReportResponse(
    val id: Int,
    val report_name: String,
    val symptoms: String,
    val pond_id: Int,
    val pond_name: String,
    val created_at: String,
    val verified: Boolean,
    val photo_url: String
)

interface ApiService {
    @Multipart
    @POST("/reports")
    suspend fun createReport(
        @Part("pond_name") pondName: RequestBody,
        @Part("report_name") reportName: RequestBody,
        @Part("symptoms") symptoms: RequestBody,
        @Part photo: MultipartBody.Part,
        @Header("Authorization") bearerToken: String
    ): Response<ReportResponse>
}

// Usage
val photoFile = File(photoPath)
val requestFile = RequestBody.create("image/jpeg".toMediaType(), photoFile)
val photoPart = MultipartBody.Part.createFormData("photo", photoFile.name, requestFile)

val response = apiService.createReport(
    RequestBody.create("text/plain".toMediaType(), "Pond A"),
    RequestBody.create("text/plain".toMediaType(), "Fish Disease Report"),
    RequestBody.create("text/plain".toMediaType(), "White spots on gills"),
    photoPart,
    "Bearer $token"
)
```

---

### 4. List Farmer's Reports

**Endpoint:** `GET /reports`

**Access:** Farmer role only

**Headers Required:**
```
Authorization: Bearer {token}
```

**Response (200 OK):**
```json
[
  {
    "id": 1,
    "report_name": "Fish Disease Report",
    "symptoms": "White spots on gills and body",
    "pond_id": 1,
    "pond_name": "Pond A",
    "created_at": "2026-05-18T10:30:45.123456",
    "verified": false,
    "photo_url": "/reports/1/photo"
  }
]
```

**Note:** Farmers can only see their own reports and their verification status (true/false), but CANNOT verify reports themselves.

**Kotlin Implementation:**
```kotlin
interface ApiService {
    @GET("/reports")
    suspend fun listReports(
        @Header("Authorization") bearerToken: String
    ): Response<List<ReportResponse>>
}
```

---

### 5. Get Single Report Detail

**Endpoint:** `GET /reports/{report_id}`

**Access:** Farmer role only (can only view own reports)

**Headers Required:**
```
Authorization: Bearer {token}
```

**Path Parameters:**
- `report_id` (required): ID of the report

**Response (200 OK):**
Same as single item in reports list

**Error Cases:**
- `404 Not Found` - Report not found or doesn't belong to farmer

**Kotlin Implementation:**
```kotlin
interface ApiService {
    @GET("/reports/{report_id}")
    suspend fun getReportDetail(
        @Path("report_id") reportId: Int,
        @Header("Authorization") bearerToken: String
    ): Response<ReportResponse>
}
```

---

### 6. Download Report Photo

**Endpoint:** `GET /reports/{report_id}/photo`

**Access:** Farmer role only

**Headers Required:**
```
Authorization: Bearer {token}
```

**Response (200 OK):**
- Binary image data

**Error Cases:**
- `404 Not Found` - Report not found

**Kotlin Implementation:**
```kotlin
interface ApiService {
    @GET("/reports/{report_id}/photo")
    suspend fun getReportPhoto(
        @Path("report_id") reportId: Int,
        @Header("Authorization") bearerToken: String
    ): Response<ResponseBody>
}
```

---

## Admin Endpoints

### 1. View All Ponds (Pending First)

**Endpoint:** `GET /admin/ponds`

**Access:** Admin role only

**Headers Required:**
```
Authorization: Bearer {token}
```

**Response (200 OK):**
```json
[
  {
    "id": 3,
    "name": "Pond C",
        "latitude": 20.035725,
        "longitude": 73.852066,
        "estimated_area": 2000.0,
        "fish_species": ["Catla"],
    "verified": false,
    "created_at": "2026-05-18T10:30:45.123456",
        "image_url": "/ponds/3/image",
    "owner_username": "farmer_john",
    "owner_phone": "+1234567890"
  },
  {
    "id": 1,
    "name": "Pond A",
        "latitude": 20.038111,
        "longitude": 73.852999,
        "estimated_area": 5000.0,
        "fish_species": ["Rohu", "Mrigal"],
    "verified": true,
    "created_at": "2026-05-17T08:15:30.123456",
        "image_url": "/ponds/1/image",
    "owner_username": "farmer_jane",
    "owner_phone": "+0987654321"
  }
]
```

**Sorting:** Pending (unverified) ponds appear first, followed by verified ponds

**Kotlin Implementation:**
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
    suspend fun listAllPonds(
        @Header("Authorization") bearerToken: String
    ): Response<List<AdminPondResponse>>
}
```

---

### 2. Verify/Unverify Pond

**Endpoint:** `PATCH /admin/ponds/{pond_id}/verify`

**Access:** Admin role only

**Headers Required:**
```
Authorization: Bearer {token}
Content-Type: application/json
```

**Path Parameters:**
- `pond_id` (required): ID of the pond

**Query Parameters:**
- `verified` (required): true or false

**Request:**
```
PATCH /admin/ponds/1/verify?verified=true
```

**Response (200 OK):**
```json
{
  "id": 1,
  "verified": true
}
```

**Error Cases:**
- `404 Not Found` - Pond not found

**Kotlin Implementation:**
```kotlin
interface ApiService {
    @PATCH("/admin/ponds/{pond_id}/verify")
    suspend fun verifyPond(
        @Path("pond_id") pondId: Int,
        @Query("verified") verified: Boolean,
        @Header("Authorization") bearerToken: String
    ): Response<Map<String, Any>>
}

// Usage
val response = apiService.verifyPond(1, true, "Bearer $token")
```

---

### 3. View All Reports (Pending First)

**Endpoint:** `GET /admin/reports`

**Access:** Admin role only

**Headers Required:**
```
Authorization: Bearer {token}
```

**Response (200 OK):**
```json
[
  {
    "id": 2,
    "report_name": "Fish Disease Report 2",
    "symptoms": "Unusual behavior and lethargy",
    "pond_id": 2,
    "pond_name": "Pond B",
    "created_at": "2026-05-18T11:45:30.123456",
    "photo_url": "/reports/2/photo",
    "verified": false,
    "farmer_username": "farmer_jane",
    "farmer_phone": "+0987654321"
  },
  {
    "id": 1,
    "report_name": "Fish Disease Report",
    "symptoms": "White spots on gills and body",
    "pond_id": 1,
    "pond_name": "Pond A",
    "created_at": "2026-05-18T10:30:45.123456",
    "photo_url": "/reports/1/photo",
    "verified": true,
    "farmer_username": "farmer_john",
    "farmer_phone": "+1234567890"
  }
]
```

**Sorting:** Pending (unverified) reports appear first

**Farmer Contact:** Admin can see farmer's phone number to contact them

**Kotlin Implementation:**
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
    suspend fun listAllReports(
        @Header("Authorization") bearerToken: String
    ): Response<List<AdminReportResponse>>
}
```

---

### 4. Verify/Unverify Report

**Endpoint:** `PATCH /admin/reports/{report_id}/verify`

**Access:** Admin role only

**Headers Required:**
```
Authorization: Bearer {token}
```

**Path Parameters:**
- `report_id` (required): ID of the report

**Query Parameters:**
- `verified` (required): true or false

**Request:**
```
PATCH /admin/reports/1/verify?verified=true
```

**Response (200 OK):**
```json
{
  "id": 1,
  "verified": true
}
```

**Error Cases:**
- `404 Not Found` - Report not found

**Kotlin Implementation:**
```kotlin
interface ApiService {
    @PATCH("/admin/reports/{report_id}/verify")
    suspend fun verifyReport(
        @Path("report_id") reportId: Int,
        @Query("verified") verified: Boolean,
        @Header("Authorization") bearerToken: String
    ): Response<Map<String, Any>>
}

// Usage - Mark report as verified
val response = apiService.verifyReport(1, true, "Bearer $token")

// Usage - Mark report as not verified (revert)
val response = apiService.verifyReport(1, false, "Bearer $token")
```

---

## Health & Status Endpoints

### 1. Health Check

**Endpoint:** `GET /health`

**Access:** Public (No token required)

**Response (200 OK):**
```json
{
  "status": "✅ Healthy",
  "yolo_model_loaded": true,
  "efficientnet_model_loaded": true,
  "message": "All models loaded and ready"
}
```

**Response (if models not ready):**
```json
{
  "status": "❌ Not Ready",
  "yolo_model_loaded": false,
  "efficientnet_model_loaded": false,
  "message": "Models not yet loaded"
}
```

**Use Case:** Call this before making prediction requests to ensure server is ready

**Kotlin Implementation:**
```kotlin
data class HealthCheckResponse(
    val status: String,
    val yolo_model_loaded: Boolean,
    val efficientnet_model_loaded: Boolean,
    val message: String
)

interface ApiService {
    @GET("/health")
    suspend fun checkHealth(): Response<HealthCheckResponse>
}

// Usage
val response = apiService.checkHealth()
if (response.isSuccessful) {
    val health = response.body()
    if (health?.yolo_model_loaded == true) {
        // Ready to make predictions
    }
}
```

---

### 2. API Information

**Endpoint:** `GET /`

**Access:** Public

**Response (200 OK):**
```json
{
  "api_name": "🐟 Fish Species Detection API",
  "version": "1.0.0",
  "description": "Three-stage fish detection pipeline: detection → species classification → disease detection",
  "endpoints": {
    "health": "/health",
    "token": "/token (POST)",
    "login": "/login (POST)",
    "logout": "/logout (POST)",
    "consumer_register": "/consumer-register (POST)",
    "farmer_register": "/farmer-register (POST)",
    "admin_register": "/admin-register (POST)",
    "predict_single": "/predict (POST)",
    "predict_batch": "/predict-batch (POST)",
    "ponds": "/ponds",
    "reports": "/reports",
    "admin_ponds": "/admin/ponds",
    "admin_reports": "/admin/reports",
    "docs": "/docs",
    "redoc": "/redoc"
  },
  "token_expiry_minutes": 1440,
  "supported_species": [
    "Catla",
    "CommonCarp",
    "Mori",
    "Rohu",
    "SilverCarp"
  ],
  "models": {
    "detection": "YOLOv8s",
    "species_classification": "EfficientNetB3",
    "disease_detection": "EfficientNetB0 (SavedModel)"
  }
}
```

---

## Common Status Codes

| Code | Meaning | Typical Cause |
|------|---------|---------------|
| 200 | OK | Request successful |
| 201 | Created | Resource created successfully |
| 400 | Bad Request | Invalid input, missing required field, file too large |
| 401 | Unauthorized | Token missing, invalid, or expired; wrong credentials |
| 403 | Forbidden | User doesn't have permission for this role |
| 404 | Not Found | Resource doesn't exist (prediction, report, pond) |
| 503 | Service Unavailable | Models still loading or server not ready |

---

## Implementation Guide for Kotlin (Android Studio)

### 1. Setup Retrofit Client

```kotlin
// build.gradle
dependencies {
    implementation 'com.squareup.retrofit2:retrofit:2.9.0'
    implementation 'com.squareup.retrofit2:converter-gson:2.9.0'
    implementation 'com.squareup.okhttp3:okhttp:4.11.0'
}

// RetrofitClient.kt
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory

object RetrofitClient {
    private const val BASE_URL = "http://localhost:8000"
    
    fun getClient(token: String? = null): Retrofit {
        val okHttpClient = okhttp3.OkHttpClient.Builder()
        
        if (!token.isNullOrEmpty()) {
            okHttpClient.addInterceptor { chain ->
                val originalRequest = chain.request()
                val requestWithAuth = originalRequest.newBuilder()
                    .header("Authorization", "Bearer $token")
                    .build()
                chain.proceed(requestWithAuth)
            }
        }
        
        return Retrofit.Builder()
            .baseUrl(BASE_URL)
            .addConverterFactory(GsonConverterFactory.create())
            .client(okHttpClient.build())
            .build()
    }
}
```

### 2. Create API Service Interface

```kotlin
import retrofit2.Response
import retrofit2.http.*
import okhttp3.MultipartBody

interface ApiService {
    // Auth endpoints
    @POST("/consumer-register")
    suspend fun registerConsumer(@Body request: ConsumerRegisterRequest): Response<UserResponse>
    
    @POST("/farmer-register")
    suspend fun registerFarmer(@Body request: FarmerRegisterRequest): Response<UserResponse>
    
    @POST("/admin-register")
    suspend fun registerAdmin(@Body request: FarmerRegisterRequest): Response<UserResponse>
    
    @POST("/login")
    suspend fun login(@Body request: LoginRequest): Response<TokenResponse>
    
    @POST("/logout")
    suspend fun logout(@Header("Authorization") bearerToken: String): Response<Map<String, String>>
    
    // Prediction endpoints (Consumer)
    @Multipart
    @POST("/predict")
    suspend fun predictFish(
        @Part file: MultipartBody.Part,
        @Header("Authorization") bearerToken: String
    ): Response<PredictionResult>
    
    @GET("/predictions")
    suspend fun getPredictionHistory(
        @Header("Authorization") bearerToken: String
    ): Response<List<PredictionHistoryItem>>
    
    @GET("/predictions/{prediction_id}")
    suspend fun getPredictionDetail(
        @Path("prediction_id") predictionId: Int,
        @Header("Authorization") bearerToken: String
    ): Response<PredictionHistoryItem>
    
    @GET("/predictions/{prediction_id}/image")
    suspend fun getPredictionImage(
        @Path("prediction_id") predictionId: Int,
        @Header("Authorization") bearerToken: String
    ): Response<ResponseBody>
    
    // Pond endpoints (Farmer)
    @POST("/ponds")
    suspend fun createPond(
        @Body request: PondCreateRequest,
        @Header("Authorization") bearerToken: String
    ): Response<PondResponse>
    
    @GET("/ponds")
    suspend fun listPonds(
        @Header("Authorization") bearerToken: String
    ): Response<List<PondResponse>>
    
    // Report endpoints (Farmer)
    @Multipart
    @POST("/reports")
    suspend fun createReport(
        @Part("pond_name") pondName: RequestBody,
        @Part("report_name") reportName: RequestBody,
        @Part("symptoms") symptoms: RequestBody,
        @Part photo: MultipartBody.Part,
        @Header("Authorization") bearerToken: String
    ): Response<ReportResponse>
    
    @GET("/reports")
    suspend fun listReports(
        @Header("Authorization") bearerToken: String
    ): Response<List<ReportResponse>>
    
    @GET("/reports/{report_id}")
    suspend fun getReportDetail(
        @Path("report_id") reportId: Int,
        @Header("Authorization") bearerToken: String
    ): Response<ReportResponse>
    
    @GET("/reports/{report_id}/photo")
    suspend fun getReportPhoto(
        @Path("report_id") reportId: Int,
        @Header("Authorization") bearerToken: String
    ): Response<ResponseBody>
    
    // Admin endpoints
    @GET("/admin/ponds")
    suspend fun listAllPonds(
        @Header("Authorization") bearerToken: String
    ): Response<List<AdminPondResponse>>
    
    @PATCH("/admin/ponds/{pond_id}/verify")
    suspend fun verifyPond(
        @Path("pond_id") pondId: Int,
        @Query("verified") verified: Boolean,
        @Header("Authorization") bearerToken: String
    ): Response<Map<String, Any>>
    
    @GET("/admin/reports")
    suspend fun listAllReports(
        @Header("Authorization") bearerToken: String
    ): Response<List<AdminReportResponse>>
    
    @PATCH("/admin/reports/{report_id}/verify")
    suspend fun verifyReport(
        @Path("report_id") reportId: Int,
        @Query("verified") verified: Boolean,
        @Header("Authorization") bearerToken: String
    ): Response<Map<String, Any>>
    
    // Health endpoint
    @GET("/health")
    suspend fun checkHealth(): Response<HealthCheckResponse>
}
```

### 3. Handle Token Management

```kotlin
// TokenManager.kt
import android.content.Context
import android.content.SharedPreferences

class TokenManager(context: Context) {
    private val preferences: SharedPreferences = 
        context.getSharedPreferences("auth", Context.MODE_PRIVATE)
    
    fun saveToken(token: String, expiresIn: Int) {
        val expiryTime = System.currentTimeMillis() + (expiresIn * 1000)
        preferences.edit()
            .putString("jwt_token", token)
            .putLong("token_expiry", expiryTime)
            .putLong("token_saved_time", System.currentTimeMillis())
            .apply()
    }
    
    fun getToken(): String? = preferences.getString("jwt_token", null)
    
    fun getTokenWithBearer(): String {
        val token = getToken()
        return if (token != null) "Bearer $token" else ""
    }
    
    fun isTokenExpired(): Boolean {
        val expiryTime = preferences.getLong("token_expiry", 0)
        return System.currentTimeMillis() >= expiryTime
    }
    
    fun clearToken() {
        preferences.edit().clear().apply()
    }
}
```

### 4. Example Repository Pattern

```kotlin
// UserRepository.kt
class UserRepository(
    private val apiService: ApiService,
    private val tokenManager: TokenManager
) {
    suspend fun login(username: String, password: String): Result<TokenResponse> {
        return try {
            val request = LoginRequest(username, password)
            val response = apiService.login(request)
            if (response.isSuccessful && response.body() != null) {
                val tokenResponse = response.body()!!
                tokenManager.saveToken(tokenResponse.access_token, tokenResponse.expires_in)
                Result.success(tokenResponse)
            } else {
                Result.failure(Exception("Login failed: ${response.code()}"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    
    suspend fun predictFish(imageFile: File): Result<PredictionResult> {
        return try {
            if (tokenManager.isTokenExpired()) {
                return Result.failure(Exception("Token expired. Please login again."))
            }
            
            val requestFile = RequestBody.create("image/jpeg".toMediaType(), imageFile)
            val body = MultipartBody.Part.createFormData("file", imageFile.name, requestFile)
            
            val response = apiService.predictFish(body, tokenManager.getTokenWithBearer())
            if (response.isSuccessful && response.body() != null) {
                Result.success(response.body()!!)
            } else {
                Result.failure(Exception("Prediction failed: ${response.code()}"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
}
```

---

## Rate Limiting & Best Practices

1. **Token Expiry:** Implement automatic token refresh or re-login when receiving 401
2. **Error Handling:** Always check `response.isSuccessful` before accessing `body()`
3. **File Uploads:** Compress images before upload for faster transmission
4. **Batch Operations:** Use `/predict-batch` for multiple images instead of sequential calls
5. **Network:** Implement retry logic with exponential backoff for network failures

---

## WebSocket Support (Future)

Real-time updates for report verification status can be added later using WebSocket connections.

---

## Support & Documentation

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
- **Health Status:** http://localhost:8000/health

---

**Last Updated:** May 18, 2026  
**API Version:** 1.0.0
