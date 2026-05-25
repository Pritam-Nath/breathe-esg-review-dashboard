# Breathe ESG ingestion prototype

Django REST + React prototype for ingesting SAP procurement/fuel, utility electricity, and corporate travel activity data, normalizing rows, surfacing failures/suspicious values, and approving/locking rows for audit.

# Preview

<img width="1920" height="1080" alt="image" src="https://github.com/user-attachments/assets/21166a56-7144-4496-8adb-26c7f5e653de" />

#

<img width="1920" height="1080" alt="image" src="https://github.com/user-attachments/assets/1618b7b8-f238-4135-8f0c-8ec77c13609d" />




## Local run

```powershell
cd D:\Codex\BreatheESG
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

In another terminal:

```powershell
cd D:\Codex\BreatheESG\frontend
npm install
npm run dev
```

Open `http://localhost:5173`, then click `Load demo`.

## Deployment notes

The app is ready for a simple split deployment:

- Backend: Render/Railway/Fly web service running `gunicorn backend.wsgi`.
- Database: Postgres in production; SQLite is used locally for the prototype.
- Frontend: static Vite build with `VITE_API_URL=https://your-backend/api`.

### Live App link 

https://breathe-esg-review-dashboard-frontend.onrender.com
