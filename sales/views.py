from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages

# Data processing and charting libraries
import pandas as pd
import io
import plotly.express as px


# This view now handles the homepage.
def home_view(request):
    return render(request, 'home.html')

# --- THIS IS THE CORRECTED LOGIN LOGIC ---
def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard') # If user is already logged in, send them to the dashboard

    if request.method == 'POST':
        # Get the username and password from the form
        username_from_form = request.POST.get('username')
        password_from_form = request.POST.get('password')

        # Use Django's authenticate function to check if credentials are valid
        user = authenticate(request, username=username_from_form, password=password_from_form)

        if user is not None:
            # If the user is valid, log them in. This creates the session.
            login(request, user)
            return redirect('dashboard') # Redirect to the dashboard upon successful login
        else:
            # If credentials are bad, show an error message.
            messages.error(request, 'Invalid username or password. Please try again.')
            return redirect('login')

    return render(request, 'login.html')

# --- THIS IS THE NEW, FUNCTIONAL REGISTRATION LOGIC ---
def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')

        # --- Validation ---
        if password != password_confirm:
            messages.error(request, "Passwords do not match.")
            return redirect('register')

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username is already taken.")
            return redirect('register')

        if User.objects.filter(email=email).exists():
            messages.error(request, "An account with this email already exists.")
            return redirect('register')

        # If all checks pass, create the new user
        user = User.objects.create_user(username=username, email=email, password=password)
        user.save()

        messages.success(request, 'Registration successful! You can now log in.')
        return redirect('login')

    return render(request, 'register.html')


# This logs the user out and redirects them.
def logout_view(request):
    logout(request)
    messages.info(request, "You have been successfully logged out.")
    return redirect('login')

@login_required(login_url='login')
def dashboard_view(request):
    context = {}

    if request.method == 'POST':
        if 'csv_file' not in request.FILES:
            messages.error(request, "No file was uploaded. Please select a CSV file.")
            return redirect('dashboard')

        csv_file = request.FILES['csv_file']

        if not csv_file.name.endswith('.csv'):
            messages.error(request, 'This is not a CSV file. Please upload a valid .csv file.')
            return redirect('dashboard')

        try:
            decoded_file = csv_file.read().decode('utf-8')
            df = pd.read_csv(io.StringIO(decoded_file))

            # --- Data preparation (this part is the same) ---
            df.rename(columns={'SALES': 'Total Revenue', 'ORDERDATE': 'Date'}, inplace=True)
            df['Date'] = pd.to_datetime(df['Date'])

            summary_html = df.describe(include='all').to_html(
                classes="w-full text-sm text-left text-gray-300",
                border=0
            )
            context['sales_summary'] = summary_html

            # --- PLOTLY CHART GENERATION (This replaces the Matplotlib code) ---

            # 1. Prepare data for the chart
            monthly_sales = df.groupby(df['Date'].dt.to_period('M'))['Total Revenue'].sum().reset_index()
            monthly_sales['Date'] = monthly_sales['Date'].dt.to_timestamp() # Convert Period to Timestamp for plotting

            # 2. Create the figure with Plotly Express
            fig = px.line(
                monthly_sales,
                x='Date',
                y='Total Revenue',
                title='Monthly Sales Trend',
                markers=True,
                labels={'Date': 'Month', 'Total Revenue': 'Total Revenue ($)'}
            )

            # 3. Update the layout for our dark theme
            fig.update_layout(
                template='plotly_dark',
                paper_bgcolor='rgba(0, 0, 0, 0)',
                plot_bgcolor='rgba(0, 0, 0, 0)',
                title_font_color='#E5E7EB',
                font_color='#9CA3AF'
            )

            # 4. Convert the figure to an HTML div
            monthly_trend_chart_html = fig.to_html(full_html=False, include_plotlyjs=False)
            context['monthly_trend_chart_html'] = monthly_trend_chart_html

            # --- END OF PLOTLY CODE ---

            context['results_exist'] = True

        except Exception as e:
            messages.error(request, f"An error occurred while processing the file: {e}")
            return redirect('dashboard')

    return render(request, 'dashboard.html', context)



@login_required(login_url='login')
def profile_view(request):
    return render(request, 'profile.html')

