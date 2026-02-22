# Deployment Guide — HAL 4.0 Secure Platform

This project is configured for **Frontend on Vercel** and **Backend on Render**.

## 1. Backend Deployment (Render)

1.  **Connect GitHub**: Sign in to [Render](https://render.com) and create a new **Blueprints** service using this repository.
2.  **blueprint.yaml**: Render will automatically detect the `render.yaml` file and set up:
    - A Python web service.
    - A PostgreSQL database (`hal-db`).
    - Necessary environment variables.
3.  **Manual Environment Variables**: In the Render Dashboard, ensure these are set (if not already generated):
    - `SECRET_KEY`: Any long random string.
    - `FERNET_KEY`: (If used for separate encryption, otherwise handled by default).
    - `DATABASE_URL`: Automatically provided by the Render Database.
4.  **Copy Backend URL**: Once deployed, copy your backend URL (e.g., `https://hal-backend.onrender.com`).

## 2. Frontend Deployment (Vercel)

1.  **Modify API URL**: Open `frontend/index.html`.
2.  Find this line:
    ```javascript
    var API = window.location.origin;
    ```
3.  **Update it** to point to your Render backend URL:
    ```javascript
    var API = "https://your-backend-url.onrender.com";
    ```
4.  **Deploy to Vercel**: 
    - Push changes to GitHub.
    - Go to [Vercel](https://vercel.com), create a new project, and select this repository.
    - Vercel will automatically use `vercel.json` to serve the `frontend/index.html`.

## 3. Environment Variables Summary

| Variable | Location | Description |
| :--- | :--- | :--- |
| `DATABASE_URL` | Render | Connection string for PostgreSQL (Auto-generated). |
| `SECRET_KEY` | Render | JWT signing key. |
| `EMAIL_ID` | Render | (Optional) Gmail ID for notifications. |
| `EMAIL_PASSWORD` | Render | (Optional) App password for notifications. |

## Troubleshooting

- **CORS Error**: The backend is currently set to `allow_origins=["*"]`. If you see CORS issues, ensure the Vercel domain is white-listed in `app/main.py`.
- **Database Migrations**: The app calls `init_db()` on startup, so tables will be created automatically on the first run.
- **Biometric Login**: For Face ID to work on the deployed site, your browser will require **HTTPS**, which both Vercel and Render provide by default.
