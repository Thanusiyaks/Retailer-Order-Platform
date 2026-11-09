 FMCG OrderHub – Deployment and Setup Guide

1. Project Overview

FMCG OrderHub is a web-based retailer ordering platform developed using React, FastAPI, and SQLite.

The application allows retailers to browse products, view prices and schemes, add products to a cart, and place orders. It also provides staff with order management and Tally-compatible CSV export functionality.

**Deployment Status:** Local development setup. The application has not been deployed to a public hosting platform.

2. Prerequisites

Install the following software before running the project:

- Python 3.10 or later
- Node.js and npm
- Visual Studio Code
- A modern web browser (Chrome or Edge)

3. Project Structure

FMCG-OrderHub/
│
├── frontend/
│   ├── src/
│   ├── public/
│   ├── package.json
│   ├── package-lock.json
│   └── index.html
│
├── backend/
│   ├── main.py
│   ├── models.py
│   ├── database.py
│   ├── seed.py
│   ├── requirements.txt
│   └── tests/
│
├── TDD.pdf
├── deployment.md
└── .gitignore

*Note: The structure above describes the main project files. The actual repository may contain additional files.*

4. Backend Setup

Step 1: Open the backend folder

Open a terminal in the project directory and run:

powershell
cd backend

Step 2: Create a virtual environment

powershell
py -m venv venv

Step 3: Install dependencies

powershell
.\venv\Scripts\python.exe -m pip install fastapi "uvicorn[standard]" sqlalchemy pytest httpx

Step 4: Initialize sample data

powershell
.\venv\Scripts\python.exe seed.py

This creates the database tables and inserts the demo accounts and sample products if they do not already exist.

Step 5: Start the backend server

powershell
.\venv\Scripts\python.exe -m uvicorn main:app --reload

Backend URL:

`http://127.0.0.1:8000`

API documentation:

`http://127.0.0.1:8000/docs`

5. Frontend Setup

Step 1: Open a second terminal

Navigate to the frontend folder from the project root:

powershell
cd frontend

Step 2: Install dependencies

powershell
npm.cmd install

Step 3: Start the frontend

powershell
npm.cmd run dev

Open the local URL displayed in the terminal. The development server may use port 5173 or another available port.

6. Database Configuration

The application uses SQLite for local data storage.

Database configuration:

- Database type: SQLite
- Database file: `fmcg_orderhub.db`
- ORM: SQLAlchemy

The database is initialized through the backend setup and sample data is inserted using `seed.py`.

7. Demo Login Credentials

The following demo accounts are available for testing.

**Retailer Account**

- Username: `retailer_demo`
- Password: `Retailer@123`
- Access: Product catalogue, cart, order placement, and own order history.

**Staff Account**

- Username: `staff_demo`
- Password: `Staff@123`
- Access: Retailer and order management, all orders, and Tally CSV export.

These credentials are for demonstration purposes only and must be changed before production use.

8. Application URLs

| Component | URL |
|---|---|
| Frontend | Local URL shown by Vite |
| Backend API | http://127.0.0.1:8000 |
| API Documentation | http://127.0.0.1:8000/docs |
| Health Check | http://127.0.0.1:8000/health |

9. Testing

The backend automated tests can be executed using:

```powershell
cd backend
.\venv\Scripts\python.exe -m pytest -v
```

The current backend test suite completed successfully with **14 passed tests**.

The following manual checks were also performed:

- Retailer login and order placement.
- Retailer access restricted to their own orders.
- Staff access to all retailer orders.
- Staff-only Tally-compatible CSV export.
- Text-based product recognition.
- Validation for unknown products and missing quantities.
- Out-of-stock product validation.

Frontend checks:

```powershell
cd frontend
npm.cmd run lint
npm.cmd run build
```

Both commands completed successfully during local verification.

10. Environment Variables and Security

The backend supports the following environment variable:

| Variable | Purpose |
|---|---|
| `JWT_SECRET_KEY` | Secret key used for signing authentication tokens. |

For production deployment, configure a strong secret key through the hosting platform's environment settings.

Do not commit secret values, passwords, or `.env` files to the GitHub repository.

The application currently uses a development fallback secret. This must be replaced with a securely configured secret before production deployment.

11. Troubleshooting

**Backend does not start**

- Check whether Python is installed.
- Verify that the virtual environment exists.
- Install the required backend dependencies.
- Check whether port 8000 is already in use.

**Frontend does not start**

- Check whether Node.js is installed.
- Run `npm.cmd install` inside the frontend folder.
- Run `npm.cmd run dev` again.

**Login does not work**

- Confirm that the backend server is running.
- Run `seed.py` to initialize demo accounts if necessary.
- Verify the username and password.

**API connection error**

- Confirm that the backend is running at `http://127.0.0.1:8000`.
- Check the browser console and backend terminal for errors.

12. Production Considerations and Future Deployment

The current version is configured for local development and demonstration.

Before production deployment, the following improvements are recommended:

- Deploy the frontend and backend to suitable hosting platforms.
- Configure a production database.
- Use a secure production secret key.
- Enable HTTPS.
- Configure production CORS settings.
- Add stronger monitoring, logging, and backup mechanisms.
- Implement advanced AI-based image and voice order capture.

The current Tally integration provides CSV export compatible with a Tally import workflow. It does not directly connect to Tally.

13. Conclusion

FMCG OrderHub provides a working demonstration of retailer ordering, product scheme calculations, order management, rule-based text order capture, and Tally-compatible CSV export.

The project can be run locally by following the setup instructions in this document.