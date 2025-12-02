# ForecastFlow 🌊 | Premium Sales Analytics

ForecastFlow is a modern, interactive web application designed to transform raw sales data from CSV files into a powerful, insightful, and easy-to-understand analytics dashboard. This project has been upgraded to a "GOATED" status with a premium UI and advanced analysis capabilities.

## ✨ Features

- **🎨 Premium "GOATED" UI**:
    - **Glassmorphism Design**: Sleek, modern dark theme with frosted glass effects.
    - **3D Background**: Interactive particle system powered by Three.js.
    - **Smooth Animations**: Float effects, transitions, and polished interactions.
    - **Responsive Grid**: Modular dashboard layout that adapts to any screen.

- **📊 Advanced Analytics Dashboard**:
    - **Dynamic Control Panel**: Switch between Overview, Sales Trends, Product Analysis, and Raw Data views instantly.
    - **Interactive Charts**: Powered by Plotly for zooming, panning, and detailed tooltips.
    - **Smart Validation**: Automatically detects required columns (`Product_name`, `Product_sold`, etc.) and maps them correctly.

- **👤 Full User Authentication**: Secure registration and login with beautiful glass-morphism forms.

## 🛠️ Tech Stack

- **Backend**: Django (Python)
- **Frontend**: Tailwind CSS, Three.js, Vanilla JS
- **Data**: Pandas, Plotly Express

## 🚀 How to Run

1.  **Clone & Setup**:
    ```bash
    git clone <repo_url>
    cd forecastflow
    python -m venv venv
    # Activate venv (Windows: .\venv\Scripts\activate, Mac/Linux: source venv/bin/activate)
    pip install -r requirements.txt
    ```

2.  **Run Server**:
    ```bash
    python manage.py migrate
    python manage.py runserver
    ```

3.  **Explore**:
    - Open `http://127.0.0.1:8000/`
    - Register an account.
    - Upload a CSV file (must have columns like `Product_name`, `Product_sold` OR `SALES`, `PRODUCTLINE`).

## ✍️ Author

**Vivek Misar**
