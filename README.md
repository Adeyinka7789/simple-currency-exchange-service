Simple Currency Exchange Service (CES)

* Python Django & Celery

## 1. Project Overview and Value Proposition
The Simple Currency Exchange Service (CES) is a high-performance, financially compliant backend application built using Python, Django, and Celery. It serves as a single source of truth for foreign exchange (FX) rates, prioritizing auditability and read performance. This project is a high-impact portfolio piece, demonstrating expertise in:
- **Asynchronous Resilience:** Using Celery Beat and Workers for guaranteed, scheduled data ingestion and retries.
- **Performance Optimization:** Implementing a full Redis caching backend for sub-10ms latency on core rate lookups.
- **Financial Integrity:** Designing an immutable data model for rates and a strict ConversionAudit log, critical for financial reconciliation.
- **Rapid Administration:** Leveraging the Django Admin for immediate visibility and management of all FX data.
- **Flexibility:** Supporting any currency pair via an EUR pivot logic, enabling dynamic conversions (e.g., USD to NGN).

## 2. Core Architectural Components
| Component         | Technology             | Role                                                                 |
|-------------------|-----------------------|----------------------------------------------------------------------|
| Web Framework     | Python / Django       | Handles synchronous API endpoints, ORM, and database transactions.   |
| Scheduled Tasks   | Celery Beat           | The scheduler that triggers rate ingestion tasks (e.g., hourly).     |
| Task Runner       | Celery Worker         | Executes external API calls, handles retries, and updates the cache. |
| Database          | PostgreSQL            | Persistent storage for historical rates and immutable audit logs.    |
| Caching/Broker    | Redis                 | Serves as both the Cache Backend (low-latency read) and Celery Broker (task queue management). |
| API               | Django Rest Framework (DRF) | Builds clean, professional RESTful endpoints. |

<img width="891" height="604" alt="image" src="https://github.com/user-attachments/assets/48c02507-0958-406b-8ab9-05f207b9401f" />

## 3. Financial Integrity & Performance Principles
### 3.1 Immutable Rate Management
The `ExchangeRate` model is designed to be history-preserving. Instead of updating a rate, the scheduled task always inserts a new record. This historical record is linked via a Foreign Key to every conversion logged in the `ConversionAudit` table, providing a non-repudiable audit trail.

### 3.2 High-Availability Ingestion
The ingestion process is decoupled from the web application via Celery. If the external FX API endpoint returns an error:
- The Celery task fails and automatically retries with an exponential backoff.
- The application continues serving the last known good rate from Redis. The API never suffers downtime due to external provider failure.

### 3.3 Low-Latency Read
All rate lookups by the Conversion API are directed to the Redis Cache using Django's built-in `cache.get()` API, ensuring maximum read speed and minimizing load on the PostgreSQL database.

### 3.4 EUR Pivot Logic
Since all rates are stored with EUR as the base currency, the system pivots through EUR to support any currency pair (e.g., USD to NGN is calculated as \((1 / \text{EUR}\rightarrow\text{USD}) \times \text{EUR}\rightarrow\text{NGN}\)), ensuring full flexibility without requiring direct pair storage.

## 4. Local Development and Setup
### 4.1 Prerequisites
- Python 3.10+
- Docker (Recommended for PostgreSQL and Redis)
- Node.js (Optional, if building Tailwind CSS locally)

### 4.2 Infrastructure Setup (Docker)
You must run a PostgreSQL database for persistence and a Redis instance to serve as both the Celery Broker and the Caching Backend.

- **Start PostgreSQL (for DB persistence):**
  ```bash
  docker run --name ces-postgres -e POSTGRES_USER=cesuser -e POSTGRES_PASSWORD=cespass -e POSTGRES_DB=cesdb -p 5432:5432 -d postgres
  ```

- **Start Redis (for Cache & Celery Broker):**
  ```bash
  docker run --name ces-redis -p 6379:6379 -d redis redis-server --appendonly yes
  ```

- **Stop/Cleanup (when done):**
  ```bash
  docker stop ces-postgres ces-redis
  docker rm ces-postgres ces-redis
  ```

### 4.3 Environment Configuration
Critical settings are loaded via environment variables (e.g., using `django-environ`).

| Variable Name    | Description                          | Rationale                          |
|-------------------|--------------------------------------|------------------------------------|
| `DATABASE_URL`    | PostgreSQL connection string.        | Standard practice for portability. |
| `REDIS_URL`       | Redis connection string (for broker/cache). | Required for Celery/Caching.       |
| `FX_API_KEY`      | API key for the external FX provider. | Security: Must be kept out of code.|
| `CONVERSION_MARGIN` | Decimal margin applied to the rate (e.g., 0.005). | Business logic parameter.          |
| `DEBUG`           | Enable/disable debug mode (e.g., True). | Convenience for local development.|

### 4.4 Running the Application
1. **Clone and Setup:**
   ```bash
   git clone [your-repository-url]
   cd currency-exchange-service
   pip install -r requirements.txt
   python manage.py migrate
   python manage.py createsuperuser  # For accessing Django Admin
   ```

2. **Start Django Server:**
   ```bash
   python manage.py runserver
   ```
   - Server running on `http://localhost:8000`
   - Django Admin available at `http://localhost:8000/admin/`

3. **Start Celery Worker (Task Execution):**
   ```bash
   celery -A ces_project worker -l info
   ```

4. **Start Celery Beat (Scheduler):**
   ```bash
   celery -A ces_project beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
   ```
   *(Note: Using `django-celery-beat` allows you to manage schedules directly via the Django Admin.)*

## 5. Key API Endpoints (DRF)
### 5.1 GET /api/rate/
- **Purpose:** Retrieves the current exchange rate, optimized for speed by querying Redis first.
- **Example:** `GET /api/rate/?base=USD&target=NGN`
- **Response:** `{"base_currency": "USD", "counter_currency": "NGN", "rate": 1557.632400, "margin": 0.005, "fetched_at": "2025-10-17T10:14:05Z"}`

### 5.2 POST /api/convert/
- **Purpose:** Executes conversion, applies margin, and creates an immutable audit record.
- **Request Body (JSON):**
  ```json
  {
      "amount": 500.00,
      "base": "USD",
      "target": "NGN"
  }
  ```
- **Response:** `{"id": "d96a29cb-6146-46cf-9845-8f606b279da9", "rate_used": {"base_currency": "EUR", "counter_currency": "NGN", ...}, "input_amount": 500.00, "output_amount": 774921.21, "margin_applied": 0.005, "converted_at": "2025-10-17T10:15:00Z", "effective_rate": 1549.842442}`

## 6. Development History & Fixes
This section documents the evolution and troubleshooting of the CES project as of October 17, 2025.

### 6.1 Initial Setup & Issues
- **Initial Error (404/Missing Data):** Encountered due to `effective_rate` mismatch in `ConversionResponseSerializer`. Fixed by adding a `SerializerMethodField` and adjusting `ConversionAPIView` to serialize before adding `effective_rate`.
- **Network Errors:** Resolved with exponential backoff in frontend fetch logic.

### 6.2 Currency Pair Flexibility
- **Issue:** "Check Rate" and "Convert Currency" only worked for USD/EUR due to direct rate lookups.
- **Fix:** Updated `ExchangeRateManager.get_latest_rate()` to pivot through EUR, calculating rates like USD→NGN via `(1 / EUR→USD) * EUR→NGN`.
- **Further Fix:** Aligned `ConversionAPIView` to use `get_latest_rate()`, resolving 404 errors for non-EUR bases.

### 6.3 Frontend Enhancements
- **Dropdown Addition:** Added client-side dropdowns in `currency.html` for dynamic currency selection, hardcoded with `CURRENCY_OPTIONS = ['USD', 'EUR', 'NGN', 'GBP', 'JPY', 'CAD', 'AUD', 'CHF', 'CNY', 'INR']`.
- **Validation:** Ensured frontend passes `base` and `target` to API calls.

### 6.4 Testing & Validation
- **Successful Test:** USD to NGN conversion (e.g., $100 → ~154,984.42 NGN) confirmed working.
- **Database Check:** Verified EUR→USD (1.17050000), EUR→CNY (8.33986462), EUR→NGN (1823.20872274) in Django shell.

## 7. API Authentication
- **Obtain Token:** Send a POST request to `/api/token/` with `{"username": "your_username", "password": "your_password"}`.
- **Use Token:** Include `Authorization: Bearer <access_token>` in the header of all API requests (e.g., `/api/rate/?base=USD&target=NGN`).
- **Refresh Token:** Use `/api/token/refresh/` with the `refresh` token to get a new `access` token.
- **Registration:** Create an account via `/api/register/` with `{"username": "your_username", "password": "your_password", "email": "your_email"}`.
- **Obtain Token:** Send a POST request to `/api/token/` with `{"username": "your_username", "password": "your_password"}`.

## 8. Future Improvements
- **Deployment:** Deploy to a public server (e.g., Heroku, AWS) using Django deployment guidelines.
- **Documentation:** Enhance with Swagger/OpenAPI spec via `drf-yasg`.
- **Rate Updates:** Ensure Celery tasks run hourly or as needed.

## 9. Acknowledgments
Developed with assistance from Genius Damilola (Fron-End : Client), Grok (xAI) on October 17, 2025. Special thanks to the community and Django ecosystem for robust tools!

---

```

---

### 📝 **Instructions**

1. **Save the File:**
   - Copy the above content into a file named `README.md` in your project directory.

2. **Review in GitHub:**
   - Commit and push to your repository. GitHub will render it nicely with tables, code blocks, and links.

3. **Local Preview:**
   - Use a Markdown viewer (e.g., Typora, VS Code with Markdown extension) to check the formatting locally.

---

### 🔧 **Changes Made**
- **Consolidated Content:** Included the original README, fixes (e.g., `get_latest_rate()`, `ConversionAPIView`), and our discussion summary.
- **Structured Sections:** Added "Development History & Fixes" (6) and "Future Improvements" (7) to document the journey.
- **Consistency:** Aligned terminology and examples with the working code (e.g., USD→NGN rates).

---

### 🚀 **NEXT STEPS**
- **Update Repository:** Replace your existing `README.md` with this version.
- **Share Feedback:** Let me know if you want to add more details or adjust sections.
- **Export Options:** If you still need a Word/PDF version, use the previous LaTeX method or convert this Markdown via tools like Pandoc (`pandoc README.md -o readme.docx` or `pandoc README.md -o readme.pdf` with LaTeX installed).

---

## 🌟 **YOUR MARKDOWN IS READY!**
This `README.md` is a complete record of your project as of 10:40 AM WAT, October 17, 2025. It’s perfect for GitHub and serves as a development log. Let me know how else I can assist! 📝💻

**Any questions or adjustments?** 🏆🚀


